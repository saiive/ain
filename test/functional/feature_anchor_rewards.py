#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test the masternodes RPC.

- verify anchors rewards
"""

from test_framework.test_framework import DefiTestFramework

from test_framework.util import assert_equal, \
    connect_nodes_bi, disconnect_nodes, wait_until

from decimal import Decimal
import time

class AnchorRewardsTest (DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 3
        self.extra_args = [
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", '-amkheight=0', "-dakotaheight=0"],
        ]
        self.setup_clean_chain = True

    def setup_network(self):
        self.setup_nodes()

        for i in range(self.num_nodes - 1):
            connect_nodes_bi(self.nodes, i, i + 1)
        self.sync_all()

    # Generate on different nodes makes more MNs available for anchor teams.
    def rotateandgenerate(self, count = 8):
        for i in range(0, count):
            self.nodes[i % self.num_nodes].generate(1)

    def mocktime(self, increment = 0):
        for i in range(0, self.num_nodes):
            self.nodes[i % self.num_nodes].set_mocktime(int(time.time() + increment))

    def setlastheight(self, height):
        for i in range(0, self.num_nodes):
            self.nodes[int(i % self.num_nodes)].spv_setlastheight(height)

    def authsquorum(self, height, node=None):
        QUORUM = 2
        if node is None:
            node = 0
        auths = self.nodes[node].spv_listanchorauths()
        for auth in auths:
            if auth['blockHeight'] == height and auth['signers'] >= QUORUM:
                return True
        return False

    def run_test(self):
        assert_equal(len(self.nodes[0].listmasternodes()), 8)

        self.mocktime(-(12 * 60 * 60))

        anchorFrequency = 15

        # Create multiple active MNs
        self.rotateandgenerate(2 * anchorFrequency)
        self.sync_all() # important to be synced before next disconnection

        assert_equal(len(self.nodes[0].spv_listanchors()), 0)

        # Mo anchors created yet as we need three hours depth in chain
        assert_equal(len(self.nodes[0].spv_listanchorauths()), 0)

        # Move forward three hours to create valida anchor data
        self.mocktime(-(9 * 60 * 60))

        # Does not generate desired number of blocks on first round! Loop it.
        blockcount = 45
        while self.nodes[0].getblockcount() < blockcount:
            diff = blockcount - self.nodes[0].getblockcount()
            self.rotateandgenerate(diff)
            self.sync_all()

        print ("Node0: Setting anchors")
        self.nodes[0].spv_setlastheight(1)
        self.nodes[1].spv_setlastheight(1)
        rewardAddress0 = self.nodes[0].getnewaddress("", "legacy")
        rewardAddress1 = self.nodes[0].getnewaddress("", "legacy")

        wait_until(lambda: self.authsquorum(15), timeout=10)
        txAnc0 = self.nodes[0].spv_createanchor([{
            'txid': "a0d5a294be3cde6a8bddab5815b8c4cb1b2ebf2c2b8a4018205d6f8c576e8963",
            'vout': 3,
            'amount': 2262303,
            'privkey': "cStbpreCo2P4nbehPXZAAM3gXXY1sAphRfEhj7ADaLx8i2BmxvEP"}],
            rewardAddress0)
        txAnc1 = self.nodes[0].spv_createanchor([{
            'txid': "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            'vout': 3,
            'amount': 2262303,
            'privkey': "cStbpreCo2P4nbehPXZAAM3gXXY1sAphRfEhj7ADaLx8i2BmxvEP"}],
            rewardAddress1)
        self.nodes[1].spv_sendrawtx(txAnc0['txHex'])
        self.nodes[1].spv_sendrawtx(txAnc1['txHex'])

        # just for triggering activation in regtest
        self.nodes[0].spv_setlastheight(1)
        self.nodes[1].spv_setlastheight(1)
        anchors = self.nodes[0].spv_listanchorspending()
        assert_equal(len(anchors), 2)

        # Trigger anchor check
        self.rotateandgenerate(1)

        # Get anchors
        anchors = self.nodes[0].spv_listanchors()
        assert_equal(len(anchors), 2)

        # print (anchors)
        if anchors[0]['active']:
            activeAnc = anchors[0]
        else:
            activeAnc = anchors[1]

        print ("Confs init:")
        assert_equal(len(self.nodes[0].spv_listanchorrewardconfirms()), 0)
        self.nodes[0].spv_setlastheight(5)
        self.nodes[1].spv_setlastheight(5)
        assert_equal(len(self.nodes[0].spv_listanchorrewardconfirms()), 0)

        # important (!) to be synced before disconnection
        # disconnect node2 (BEFORE reward voting!) for future rollback
        disconnect_nodes(self.nodes[1], 2)

        self.nodes[0].spv_setlastheight(6)
        self.nodes[1].spv_setlastheight(6)
        # important to wait here!
        self.sync_blocks(self.nodes[0:2])
        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 1 and self.nodes[0].spv_listanchorrewardconfirms()[0]['signers'] == 2, timeout=10)

        conf0 = self.nodes[0].spv_listanchorrewardconfirms()
        print ("Confs created, only active anchor:", conf0)
        assert_equal(len(conf0), 1)
        assert_equal(conf0[0]['anchorHeight'], 15)
        assert_equal(conf0[0]['prevAnchorHeight'], 0)
        assert_equal(conf0[0]['rewardAddress'], activeAnc['rewardAddress'])
        assert_equal(conf0[0]['signers'], 2)

        print ("Generate reward")
        assert_equal(len(self.nodes[0].spv_listanchorrewards()), 0)

        self.nodes[0].generate(1)

        # confirms should disappear
        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 0, timeout=10)

        # check reward tx
        rew0 = self.nodes[0].spv_listanchorrewards()

        assert_equal(len(rew0), 1)
        assert_equal(rew0[0]['AnchorTxHash'], conf0[0]['btcTxHash'])
        rew0tx = self.nodes[0].decoderawtransaction(self.nodes[0].getrawtransaction(rew0[0]['RewardTxHash']))

        assert_equal(rew0tx['vout'][1]['scriptPubKey']['addresses'][0], conf0[0]['rewardAddress'])
        assert_equal(rew0tx['vout'][1]['value'], Decimal('4.60000000')) # Height 46 * 0.1

        print ("Rollback!")
        self.nodes[2].generate(2)
        connect_nodes_bi(self.nodes, 1, 2)
        self.sync_all()

        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 1, timeout=10) # while rollback, it should appear w/o wait
        assert_equal(len(self.nodes[0].spv_listanchorrewards()), 0)
        wait_until(lambda: len(self.nodes[2].spv_listanchorrewardconfirms()) == 1, timeout=10) # but wait here
        assert_equal(len(self.nodes[2].spv_listanchorrewards()), 0)

        print ("Reward again")
        self.nodes[1].generate(1)
        self.sync_all()

        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 0, timeout=10)
        assert_equal(len(self.nodes[0].spv_listanchorrewards()), 1)

        print ("Generate more (2 unpaid rewards at once)")
        self.setlastheight(6)

        # Move forward slowly to avoid future block error
        for i in range(8, 2, -1):
            self.mocktime(-(i * 60 * 60))
            self.rotateandgenerate(5)
        self.sync_all()
        wait_until(lambda: self.authsquorum(60), timeout=10)

        rewardAddress2 = self.nodes[0].getnewaddress("", "legacy")
        txAnc2 = self.nodes[0].spv_createanchor([{
            'txid': "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            'vout': 3,
            'amount': 2262303,
            'privkey': "cStbpreCo2P4nbehPXZAAM3gXXY1sAphRfEhj7ADaLx8i2BmxvEP"}],
            rewardAddress2)
        self.nodes[1].spv_sendrawtx(txAnc2['txHex'])

        self.nodes[0].spv_setlastheight(7)
        self.nodes[1].spv_setlastheight(7)

        # Move forward slowly to avoid future block error
        for i in range(2, -1, -1):
            self.mocktime(-(i * 60 * 60))
            self.rotateandgenerate(anchorFrequency)

        self.sync_all()
        wait_until(lambda: self.authsquorum(75), timeout=10)

        # for rollback. HERE, to deny cofirmations for node2
        disconnect_nodes(self.nodes[1], 2)

        self.nodes[0].spv_setlastheight(13)
        self.nodes[1].spv_setlastheight(13)

        # important to wait here!
        self.sync_blocks(self.nodes[0:2])

        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 1 and self.nodes[0].spv_listanchorrewardconfirms()[0]['signers'] == 2, timeout=10)

        # check confirmations (revoting) after node restart:
        self.stop_node(0)
        self.start_node(0, ['-txindex=1', '-amkheight=0', "-dakotaheight=0"])
        connect_nodes_bi(self.nodes, 0, 1)
        self.sync_blocks(self.nodes[0:2])
        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 1 and self.nodes[0].spv_listanchorrewardconfirms()[0]['signers'] == 2, timeout=10)

        self.nodes[1].generate(1)
        self.sync_blocks(self.nodes[0:2])
        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 0, timeout=10)

        assert_equal(len(self.nodes[0].spv_listanchorrewards()), 2)

        # check reward of anc2 value (should be 5)
        rew = self.nodes[0].spv_listanchorrewards()
        for i in rew:
            if i['AnchorTxHash'] == txAnc2['txHash']:
                rew2Hash = i['RewardTxHash']
        rew2tx = self.nodes[0].decoderawtransaction(self.nodes[0].getrawtransaction(rew2Hash))
        assert_equal(rew2tx['vout'][1]['scriptPubKey']['addresses'][0], rewardAddress2)
        assert_equal(rew2tx['vout'][1]['value'], Decimal('7.60000000'))

        print ("Rollback a rewards")
        self.nodes[2].generate(3)
        connect_nodes_bi(self.nodes, 1, 2)
        self.sync_all()
        wait_until(lambda: len(self.nodes[0].spv_listanchorrewardconfirms()) == 1, timeout=10)
        assert_equal(len(self.nodes[0].spv_listanchorrewards()), 1)

if __name__ == '__main__':
    AnchorRewardsTest().main()
