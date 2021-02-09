#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test the Dakota anchorsC."""

from test_framework.test_framework import DefiTestFramework
from test_framework.util import assert_equal, connect_nodes, wait_until

from decimal import Decimal
import time

class AnchorDakotaTest (DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 8
        self.extra_args = [
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
            [ "-dummypos=1", "-spv=1", "-fakespv=1", "-txindex=1", "-anchorquorum=2", '-amkheight=0', "-dakotaheight=0"],
        ]
        self.setup_clean_chain = True

    def setup_network(self):
        self.setup_nodes()

        # Connect all nodes to all nodes
        for i in range(0, self.num_nodes):
            for j in range(0, self.num_nodes):
                connect_nodes(self.nodes[i], j)

        self.sync_all()

    # Generate on different nodes makes more MNs available for anchor teams.
    def rotateandgenerate(self, count = 8):
        for i in range(0, count):
            self.nodes[i % self.num_nodes].generate(1)

    def mocktime(self, increment = 3 * 60 * 60):
        for i in range(0, self.num_nodes):
            self.nodes[i % self.num_nodes].set_mocktime(int(time.time() + increment))

    def setlastheight(self, height):
        for i in range(0, self.num_nodes):
            self.nodes[int(i % self.num_nodes)].spv_setlastheight(height)

    # Send same anchor on each node
    def createanchor(self, reward_address):
        tx = self.nodes[0].spv_createanchor([{
            'txid': "a0d5a294be3cde6a8bddab5815b8c4cb1b2ebf2c2b8a4018205d6f8c576e8963",
            'vout': 3,
            'amount': 2262303,
            'privkey': "cStbpreCo2P4nbehPXZAAM3gXXY1sAphRfEhj7ADaLx8i2BmxvEP"}],
            reward_address,
            True,
            2000)
        for i in range(1, self.num_nodes):
            self.nodes[i].spv_sendrawtx(tx['txHex'])

    def run_test(self):
        assert_equal(len(self.nodes[0].listmasternodes()), 8)
        assert_equal(len(self.nodes[0].spv_listanchors()), 0)

        anchorFrequency = 15

        # Create multiple active MNs
        self.rotateandgenerate(2 * anchorFrequency)

        assert_equal(len(self.nodes[0].getanchorteams()['auth']), 3)
        assert_equal(len(self.nodes[0].getanchorteams()['confirm']), 3)

        # Mo anchors created yet as we need three hours depth in chain
        assert_equal(len(self.nodes[0].spv_listanchorauths()), 0)

        # Move forward three hours to create valida anchor data
        self.mocktime()

        # Does not generate desired number of blocks on first round! Loop it.
        blockcount = 45
        while self.nodes[0].getblockcount() < blockcount:
            diff = blockcount - self.nodes[0].getblockcount()
            self.rotateandgenerate(diff)
            self.sync_all()

        # Anchor data
        auth = self.nodes[0].spv_listanchorauths()
        assert_equal(len(auth), 1)
        assert_equal(auth[0]['creationHeight'], 45)
        assert_equal(auth[0]['blockHeight'], 15)
        assert_equal(auth[0]['signers'], 3)

        hash15 = self.nodes[0].getblockhash(15)
        hash45 = self.nodes[0].getblockhash(45)
        block15 = self.nodes[0].getblock(hash15)
        block45 = self.nodes[0].getblock(hash45)

        # Check the time
        time_diff = block45['time'] - block15['time']
        assert(time_diff > 3 * 60 * 60)

        # Bitcoin block 15
        self.setlastheight(15)

        reward_address = self.nodes[0].getnewaddress("", "legacy")

        # Create anchor
        self.createanchor(reward_address)

        # Anchor pending
        assert_equal(len(self.nodes[0].spv_listanchors()), 0)
        pending = self.nodes[0].spv_listanchorspending()
        assert_equal(len(pending), 1)
        assert_equal(pending[0]['btcBlockHeight'], 15)
        assert_equal(pending[0]['defiBlockHeight'], 15)
        assert_equal(pending[0]['rewardAddress'], reward_address)
        assert_equal(pending[0]['confirmations'], 1) # Bitcoin confirmations
        assert_equal(pending[0]['signatures'], 2)
        assert_equal(pending[0]['anchorCreationHeight'], 45)

        # Check these are consistent across anchors life
        btcHash = pending[0]['btcTxHash']
        dfiHash = pending[0]['defiBlockHash']

        # Trigger anchor check
        self.rotateandgenerate(1)

        # Anchor
        assert_equal(len(self.nodes[0].spv_listanchorsunrewarded()), 0)
        assert_equal(len(self.nodes[0].spv_listanchorspending()), 0)
        anchors = self.nodes[0].spv_listanchors()
        assert_equal(len(anchors), 1)
        assert_equal(anchors[0]['btcBlockHeight'], 15)
        assert_equal(anchors[0]['btcTxHash'], btcHash)
        assert_equal(anchors[0]['previousAnchor'], '0000000000000000000000000000000000000000000000000000000000000000')
        assert_equal(anchors[0]['defiBlockHeight'], 15)
        assert_equal(anchors[0]['defiBlockHash'], dfiHash)
        assert_equal(anchors[0]['rewardAddress'], reward_address)
        assert_equal(anchors[0]['confirmations'], 1) # Bitcoin confirmations
        assert_equal(anchors[0]['signatures'], 2)
        assert_equal(anchors[0]['anchorCreationHeight'], 45)
        assert_equal(anchors[0]['active'], False)

        # Still not active
        self.setlastheight(19)

        anchors = self.nodes[0].spv_listanchors()
        assert_equal(anchors[0]['confirmations'], 5) # Bitcoin confirmations
        assert_equal(anchors[0]['active'], False)

        # Activate here
        self.setlastheight(20)

        anchors = self.nodes[0].spv_listanchors()
        assert_equal(anchors[0]['confirmations'], 6) # Bitcoin confirmations
        assert_equal(anchors[0]['active'], True)

        unrewarded = self.nodes[0].spv_listanchorsunrewarded()
        assert_equal(len(unrewarded), 1)
        assert_equal(unrewarded[0]['btcHeight'], 15)
        assert_equal(unrewarded[0]['btcHash'], btcHash)
        assert_equal(unrewarded[0]['dfiHeight'], 15)
        assert_equal(unrewarded[0]['dfiHash'], dfiHash)

        for i in range(0, self.num_nodes):
            wait_until(lambda: len(self.nodes[i].spv_listanchorrewardconfirms()) == 1 and self.nodes[i].spv_listanchorrewardconfirms()[0]['signers'] == 3, timeout=2)

        # Should be height 46 so reward 46 x 0.1. Hard code value here for simplicity!
        assert_equal(self.nodes[0].listcommunitybalances()['AnchorReward'], Decimal('4.60000000'))

        reward = self.nodes[0].listcommunitybalances()['AnchorReward']

        # Mine anchor reward
        self.rotateandgenerate(1)

        block_count = self.nodes[0].getblockcount() # 47
        block_hash = self.nodes[0].getblockhash(block_count)
        block = self.nodes[0].getblock(block_hash)

        # Reward should be reset and block contains two TXs
        assert_equal(self.nodes[0].listcommunitybalances()['AnchorReward'], Decimal('0.10000000'))
        assert_equal(len(block['tx']), 2)

        tx = block['tx'][1]
        raw_tx = self.nodes[0].getrawtransaction(tx, 1)

        # Check reward
        assert_equal(len(raw_tx['vout']), 2)
        assert_equal(raw_tx['vout'][1]['value'], reward)
        assert_equal(raw_tx['vout'][1]['scriptPubKey']['addresses'][0], reward_address)

        # Check data from list transactions
        anchors = self.nodes[0].listanchors()
        assert_equal(anchors[0]['anchorHeight'], 15)
        assert_equal(anchors[0]['anchorHash'], dfiHash)
        assert_equal(anchors[0]['rewardAddress'], reward_address)
        assert_equal(anchors[0]['dfiRewardHash'], tx)
        assert_equal(anchors[0]['btcAnchorHeight'], 15)
        assert_equal(anchors[0]['btcAnchorHash'], btcHash)

if __name__ == '__main__':
    AnchorDakotaTest().main()
