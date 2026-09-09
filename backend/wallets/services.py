from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from associates.models import Associate
from wallets.models import LedgerEntry, Wallet


class WalletService:
    ALL_TYPES = [c.value for c in Wallet.WalletType]

    @staticmethod
    def ensure_wallets(associate: Associate) -> list[Wallet]:
        wallets = []
        for wtype in WalletService.ALL_TYPES:
            wallet, _ = Wallet.objects.get_or_create(
                associate=associate,
                wallet_type=wtype,
                defaults={"balance": Decimal("0.00")},
            )
            wallets.append(wallet)
        return wallets

    @staticmethod
    @transaction.atomic
    def credit(
        *,
        associate: Associate,
        wallet_type: str,
        amount: Decimal,
        reference: str = "",
        narration: str = "",
        meta: dict | None = None,
    ) -> LedgerEntry:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        wallet = Wallet.objects.select_for_update().get(associate=associate, wallet_type=wallet_type)
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])
        return LedgerEntry.objects.create(
            wallet=wallet,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount=amount,
            balance_after=wallet.balance,
            reference=reference,
            narration=narration,
            meta=meta or {},
        )

    @staticmethod
    @transaction.atomic
    def debit(
        *,
        associate: Associate,
        wallet_type: str,
        amount: Decimal,
        reference: str = "",
        narration: str = "",
        meta: dict | None = None,
    ) -> LedgerEntry:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        wallet = Wallet.objects.select_for_update().get(associate=associate, wallet_type=wallet_type)
        available = wallet.balance - wallet.held_balance
        if available < amount:
            raise ValueError("Insufficient wallet balance")
        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])
        return LedgerEntry.objects.create(
            wallet=wallet,
            entry_type=LedgerEntry.EntryType.DEBIT,
            amount=amount,
            balance_after=wallet.balance,
            reference=reference,
            narration=narration,
            meta=meta or {},
        )
