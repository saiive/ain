#!/usr/bin/env python3
# Copyright (c) 2014-2020 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test token's RPC.

- verify before fork, not allow create token, after fork can create token
"""

from test_framework.test_framework import DefiTestFramework

from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal

class TokensForkTest (DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [['-txnotokens=0', '-amkheight=120'], ['-txnotokens=0', '-amkheight=120']]

    def run_test(self):
        assert_equal(len(self.nodes[0].listtokens()), 1) # only one token == DFI

        self.nodes[0].generate(100)
        self.sync_blocks()

        self.nodes[0].generate(2) # for 2 matured utxos

        # Try to create token before AMK fork height but will fail:
        #========================
        collateralGold = self.nodes[0].getnewaddress("", "legacy")
        collateralSilver = self.nodes[0].getnewaddress("", "legacy")
        try:
            self.nodes[0].createtoken([], {
                "symbol": "GOLD",
                "name": "shiny gold",
                "collateralAddress": collateralGold
            })
            self.nodes[0].createtoken([], {
                "symbol": "SILVER",
                "name": "just silver",
                "collateralAddress": collateralSilver
            })
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("No tokenization transaction before block height" in errorString)

        self.nodes[0].generate(1)
        # Before fork, create should fail, so now only have default token
        tokens = self.nodes[0].listtokens()
        assert_equal(len(tokens), 1)

        # Try to destroy token before AMK fork height but will fail:
        #========================
        try:
            self.nodes[0].destroytoken([], "GOLD")
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("No tokenization transaction before block height" in errorString)

        # Try to mint token before AMK fork height but will fail:
        #========================
        try:
            self.nodes[0].minttokens([], "300@GOLD")
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("No tokenization transaction before block height" in errorString)

        self.nodes[0].generate(17)
        self.sync_blocks()

        # Now at AMK height 120
        # Now create again, it should pass
        self.nodes[0].createtoken([], {
            "symbol": "GOLD",
            "name": "shiny gold",
            "collateralAddress": collateralGold
        })
        self.nodes[0].createtoken([], {
            "symbol": "SILVER",
            "name": "just silver",
            "collateralAddress": collateralSilver
        })

        self.nodes[0].generate(1)
        # After fork, create should pass, so now only have 3 kind of tokens
        tokens = self.nodes[0].listtokens()
        assert_equal(len(tokens), 3)

        list_tokens = self.nodes[0].listtokens()
        for idx, token in list_tokens.items():
            if (token["symbol"] == "GOLD"):
                idGold = idx
            if (token["symbol"] == "SILVER"):
                idSilver = idx

        symbolGold = "GOLD#" + idGold
        symbolSilver = "SILVER#" + idSilver

        self.sync_blocks()

        # MINT:
        #========================
        # Funding auth addresses

        self.nodes[0].sendmany("", { collateralGold : 1, collateralSilver : 1 })
        self.nodes[0].generate(1)
        self.nodes[0].sendmany("", { collateralGold : 1, collateralSilver : 1 })
        self.nodes[0].generate(1)

        # print(self.nodes[0].listunspent())

        alienMintAddr = self.nodes[1].getnewaddress("", "legacy")
        self.nodes[0].minttokens([], "300@" + symbolGold)
        self.nodes[0].minttokens([], "3000@" + symbolSilver)
        self.nodes[0].generate(1)
        self.sync_blocks()

        self.nodes[0].accounttoutxos([], collateralGold, { self.nodes[0].getnewaddress("", "legacy"): "100@" + symbolGold, alienMintAddr: "200@" + symbolGold})
        self.nodes[0].accounttoutxos([], collateralSilver, { self.nodes[0].getnewaddress("", "legacy"): "1000@" + symbolSilver, alienMintAddr: "2000@" + symbolSilver})
        self.nodes[0].generate(1)
        self.sync_blocks()

        assert_equal(self.nodes[0].getbalances(True)['mine']['trusted'][str(idGold)], 100)
        assert_equal(self.nodes[1].getbalances(True)['mine']['trusted'][str(idGold)], 200)
        assert_equal(self.nodes[0].getbalances(True)['mine']['trusted'][str(idSilver)], 1000)
        assert_equal(self.nodes[1].getbalances(True)['mine']['trusted'][str(idSilver)], 2000)

        print ("Check 'sendmany' for tokens")
        alienSendAddr = self.nodes[1].getnewaddress("", "legacy")
        # check sending of different tokens on same address
        self.nodes[0].sendmany("", { alienSendAddr : [ str(10) + "@" + symbolGold, str(20) + "@" + symbolSilver] })
        self.nodes[0].generate(1)
        self.sync_blocks()

        assert_equal(self.nodes[0].getbalances(True)['mine']['trusted'][str(idGold)], 90)
        assert_equal(self.nodes[0].getbalances(True)['mine']['trusted'][str(idSilver)], 980)
        assert_equal(self.nodes[1].getbalances(True)['mine']['trusted'][str(idGold)], 210)
        assert_equal(self.nodes[1].getbalances(True)['mine']['trusted'][str(idSilver)], 2020)


if __name__ == '__main__':
    TokensForkTest ().main ()