from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from associates.models import Associate
from core.models import BaseModel


class Wallet(BaseModel):
    class WalletType(models.TextChoices):
        MAIN = "main", "Main Fund"
        PERSONAL = "personal", "Personal Fund"
        INCOME = "income", "Income Wallet"
        REWARD = "reward", "Reward Wallet"
        ROI = "roi", "ROI Wallet"
        WITHDRAW = "withdraw", "Withdraw Wallet"

    associate = models.ForeignKey(Associate, on_delete=models.CASCADE, related_name="wallets")
    wallet_type = models.CharField(max_length=20, choices=WalletType.choices)
    balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    held_balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="INR")

    class Meta:
        unique_together = ("associate", "wallet_type")
        indexes = [models.Index(fields=["associate", "wallet_type"])]

    def __str__(self) -> str:
        return f"{self.associate.associate_id}:{self.wallet_type}={self.balance}"


class LedgerEntry(BaseModel):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="entries")
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    balance_after = models.DecimalField(max_digits=16, decimal_places=2)
    reference = models.CharField(max_length=80, blank=True, db_index=True)
    narration = models.CharField(max_length=255, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["wallet", "created_at"])]


class InvestmentBusinessApplication(BaseModel):
    """Durable, one-time marker for an investment business source event."""

    source_reference = models.CharField(max_length=80, unique=True)
    associate = models.ForeignKey(
        Associate,
        on_delete=models.PROTECT,
        related_name="investment_business_applications",
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.source_reference} → {self.associate.associate_id} {self.amount}"


class FundTransferRequest(BaseModel):
    """Associate asks admin to credit a package. Only staff can approve/execute."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    requester = models.ForeignKey(
        Associate, on_delete=models.CASCADE, related_name="fund_transfer_requests"
    )
    beneficiary = models.ForeignKey(
        Associate, on_delete=models.CASCADE, related_name="fund_transfer_credits_requested"
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    wallet_type = models.CharField(max_length=20, default=Wallet.WalletType.MAIN)
    payment_method = models.CharField(max_length=40)
    utr = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="UTR / bank or UPI transaction ID from the associate.",
    )
    proof = models.FileField(
        upload_to="fund-transfers/proofs/%Y/%m/",
        blank=True,
        null=True,
        help_text="Payment screenshot, receipt, or PDF.",
    )
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fund_transfer_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    ledger_entry = models.ForeignKey(
        LedgerEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fund_transfer_requests",
    )
    apply_business = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
        verbose_name = "Fund transfer request"
        permissions = [
            ("can_fund_transfer", "Can execute fund transfers"),
        ]

    def __str__(self) -> str:
        return f"{self.requester.associate_id} → {self.beneficiary.associate_id} {self.amount} ({self.status})"
