
#include <chainparams.h>
#include <masternodes/vault.h>

Res CVaultView::StoreVault(const CVaultId& vaultId, const CVaultData& vault)
{
    WriteBy<VaultKey>(vaultId, vault);
    return Res::Ok();
}

boost::optional<CVaultData> CVaultView::GetVault(const CVaultId& vaultId) const
{
    return ReadBy<VaultKey, CVaultData>(vaultId);
}

Res CVaultView::UpdateVault(const CVaultId& vaultId, const CVaultMessage& newVault)
{
    auto vault = GetVault(vaultId);
    if (!vault) {
        return Res::Err("Vault <%s> not found", vaultId.GetHex());
    }

    vault->ownerAddress = newVault.ownerAddress;
    vault->schemeId = newVault.schemeId;

    WriteBy<VaultKey>(vaultId, *vault);
    return Res::Ok();
}

void CVaultView::ForEachVault(std::function<bool(const CVaultId&, const CVaultData&)> callback)
{
    ForEach<VaultKey, CVaultId, CVaultData>(callback);
}

Res CVaultView::AddVaultCollateral(const CVaultId& vaultId, CTokenAmount amount)
{
    CBalances amounts;
    ReadBy<CollateralKey>(vaultId, amounts);
    auto res = amounts.Add(amount);
    if (!res) {
        return res;
    }
    if (!amounts.balances.empty()) {
        WriteBy<CollateralKey>(vaultId, amounts);
    }
    return Res::Ok();
}

Res CVaultView::SubVaultCollateral(const CVaultId& vaultId, CTokenAmount amount)
{
    auto amounts = GetVaultCollaterals(vaultId);
    if (!amounts || !amounts->Sub(amount)) {
        return Res::Err("Collateral for vault <%s> not found", vaultId.GetHex());
    }
    if (amounts->balances.empty()) {
        EraseBy<CollateralKey>(vaultId);
    } else {
        WriteBy<CollateralKey>(vaultId, *amounts);
    }
    return Res::Ok();
}

boost::optional<CBalances> CVaultView::GetVaultCollaterals(const CVaultId& vaultId)
{
    return ReadBy<CollateralKey, CBalances>(vaultId);
}

void CVaultView::ForEachVaultCollateral(std::function<bool(const CVaultId&, const CBalances&)> callback)
{
    ForEach<CollateralKey, CVaultId, CBalances>(callback);
}

Res CVaultView::StoreAuction(const CVaultId& vaultId, uint32_t height, const CAuctionData& data)
{
    auto auctionHeight = height + Params().GetConsensus().blocksCollateralAuction();
    WriteBy<AuctionHeightKey>(AuctionKey{vaultId, auctionHeight}, data);
    return Res::Ok();
}

Res CVaultView::EraseAuction(const CVaultId& vaultId, uint32_t height)
{
    auto it = LowerBound<AuctionHeightKey>(AuctionKey{vaultId, height});
    for (; it.Valid(); it.Next()) {
        if (it.Key().vaultId == vaultId) {
            CAuctionData data = it.Value();
            for (uint32_t i = 0; i < data.batchCount; i++) {
                EraseAuctionBid(vaultId, i);
                EraseAuctionBatch(vaultId, i);
            }
            EraseBy<AuctionHeightKey>(it.Key());
            return Res::Ok();
        }
    }
    return Res::Err("Auction for vault <%s> not found", vaultId.GetHex());
}

boost::optional<CAuctionData> CVaultView::GetAuction(const CVaultId& vaultId, uint32_t height)
{
    auto it = LowerBound<AuctionHeightKey>(AuctionKey{vaultId, height});
    for (; it.Valid(); it.Next()) {
        if (it.Key().vaultId == vaultId) {
            return it.Value().as<CAuctionData>();
        }
    }
    return {};
}

Res CVaultView::StoreAuctionBatch(const CVaultId& vaultId, uint32_t id, const CAuctionBatch& batch)
{
    WriteBy<AuctionBatchKey>(std::make_pair(vaultId, id), batch);
    return Res::Ok();
}

Res CVaultView::EraseAuctionBatch(const CVaultId& vaultId, uint32_t id)
{
    EraseBy<AuctionBatchKey>(std::make_pair(vaultId, id));
    return Res::Ok();
}

boost::optional<CAuctionBatch> CVaultView::GetAuctionBatch(const CVaultId& vaultId, uint32_t id)
{
    return ReadBy<AuctionBatchKey, CAuctionBatch>(std::make_pair(vaultId, id));
}

void CVaultView::ForEachVaultAuction(std::function<bool(const AuctionKey&, const CAuctionData&)> callback, AuctionKey const & start)
{
    ForEach<AuctionHeightKey, AuctionKey, CAuctionData>([&](const AuctionKey& auction, const CAuctionData& data) {
        return callback(auction, data);
    }, start);
}

Res CVaultView::StoreAuctionBid(const CVaultId& vaultId, uint32_t id, COwnerTokenAmount amount)
{
    WriteBy<AuctionBidKey>(std::make_pair(vaultId, id), amount);
    return Res::Ok();
}

Res CVaultView::EraseAuctionBid(const CVaultId& vaultId, uint32_t id)
{
    EraseBy<AuctionBidKey>(std::make_pair(vaultId, id));
    return Res::Ok();
}

boost::optional<CVaultView::COwnerTokenAmount> CVaultView::GetAuctionBid(const CVaultId& vaultId, uint32_t id)
{
    return ReadBy<AuctionBidKey, COwnerTokenAmount>(std::make_pair(vaultId, id));
}
