"""Hide the investor's own monthly ROI (₹2,200). It is a calculation base only."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Q, Sum

from wallets.models import LedgerEntry, Wallet

# Buyer self-credit: MRI-{contract}-M{n}  (no -L{depth})
# Narration from older builds: "Monthly ROI M1" / "ROI M1"
BUYER_SELF_ROI_Q = (
    Q(reference__regex=r"MRI-.+-M\d+$")
    | Q(narration__iregex=r"^(Monthly )?ROI M\d+")
    | Q(narration__icontains="Monthly ROI M")
)


def exclude_buyer_self_roi(qs):
    return qs.exclude(BUYER_SELF_ROI_Q)


def buyer_self_roi_credited(wallet: Wallet) -> Decimal:
    if wallet.wallet_type != Wallet.WalletType.ROI:
        return Decimal("0.00")
    total = (
        LedgerEntry.objects.filter(
            wallet=wallet,
            entry_type=LedgerEntry.EntryType.CREDIT,
            is_deleted=False,
        )
        .filter(BUYER_SELF_ROI_Q)
        .aggregate(total=Sum("amount"))["total"]
    )
    return total or Decimal("0.00")


def visible_wallet_balance(wallet: Wallet) -> Decimal:
    raw = wallet.balance or Decimal("0.00")
    hidden = buyer_self_roi_credited(wallet)
    visible = raw - hidden
    return visible if visible > 0 else Decimal("0.00")
