"""Admin wallet purge — remove ledger entries then the wallet (PROTECT-safe)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from wallets.models import LedgerEntry, Wallet


class WalletPurgeError(ValueError):
    """Raised when a wallet cannot be removed."""


def _soft_qs(qs) -> int:
    count = qs.filter(is_deleted=False).count()
    if count:
        qs.filter(is_deleted=False).delete(soft=True)
    return count


def _hard_qs(qs) -> int:
    count = qs.count()
    if count:
        qs.delete(force=True)
    return count


@transaction.atomic
def purge_wallet(*, wallet: Wallet, hard: bool = False) -> dict:
    """
    Remove a wallet and its ledger rows from the live app.

    Default (hard=False): soft-delete ledger entries, zero balance, soft-delete wallet.
    hard=True: permanently destroy ledger + wallet (superuser only).
    """
    w = Wallet.all_objects.select_for_update().get(pk=wallet.pk)
    assoc = w.associate
    remove = _hard_qs if hard else _soft_qs

    ledger_n = remove(LedgerEntry.all_objects.filter(wallet_id=w.pk))

    if not hard:
        if w.balance or w.held_balance:
            w.balance = Decimal("0.00")
            w.held_balance = Decimal("0.00")
            w.save(update_fields=["balance", "held_balance", "updated_at"])
        w.delete(soft=True)
    else:
        w.delete(force=True)

    return {
        "wallet": str(w),
        "associate_id": assoc.associate_id,
        "wallet_type": w.wallet_type,
        "ledger_removed": ledger_n,
        "hard": hard,
    }
