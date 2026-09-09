from decimal import Decimal

from django.db import models
from django.db.models import Count, Sum

from associates.models import Associate
from core.models import BaseModel


class CommissionRun(BaseModel):
    class RunType(models.TextChoices):
        LEVEL = "level", "Level Income"
        PERFORMANCE = "performance", "Performance Income"
        ROI = "roi", "ROI Income"
        REWARD = "reward", "Reward Income"
        DIRECT = "direct", "Direct Income"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    run_type = models.CharField(max_length=20, choices=RunType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source_reference = models.CharField(max_length=80, blank=True)
    source_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.run_type}:{self.status}:{self.source_reference}"

    def payout_summary(self) -> dict:
        """Totals for Finance → Commission Runs (ROI-on-ROI and other run types)."""
        qs = self.entries.filter(is_deleted=False).exclude(status=CommissionEntry.Status.VOIDED)
        credited = qs.filter(status=CommissionEntry.Status.CREDITED)
        skipped = qs.filter(status=CommissionEntry.Status.SKIPPED)
        paid = credited.aggregate(total=Sum("amount"), n=Count("id"), people=Count("beneficiary_id", distinct=True))
        level_commissions = {}
        for row in credited.values("level").annotate(total=Sum("amount"), n=Count("id")).order_by("level"):
            level_commissions[str(row["level"])] = {
                "amount": str(row["total"] or Decimal("0")),
                "count": row["n"],
            }
        return {
            "total_roi_generated": str(self.source_amount or Decimal("0")),
            "total_level_commission": str(paid["total"] or Decimal("0")),
            "level_commissions": level_commissions,
            "beneficiaries": int(paid["people"] or 0),
            "successful_entries": int(paid["n"] or 0),
            "failed_entries": skipped.count(),
        }


class CommissionEntry(BaseModel):
    """Commission ledger row — one credited payout per beneficiary/level/sale reference."""

    class Status(models.TextChoices):
        CREDITED = "credited", "Credited"
        SKIPPED = "skipped", "Skipped"
        VOIDED = "voided", "Voided"

    run = models.ForeignKey(CommissionRun, on_delete=models.CASCADE, related_name="entries")
    beneficiary = models.ForeignKey(Associate, on_delete=models.PROTECT, related_name="commission_entries")
    source_associate = models.ForeignKey(
        Associate,
        on_delete=models.PROTECT,
        related_name="generated_commissions",
        null=True,
        blank=True,
        help_text="Buyer / associate whose sale generated this commission",
    )
    level = models.PositiveIntegerField(
        default=0,
        help_text="Network / upline depth (1–10). 0 = investor ROI credit.",
    )
    growth_level = models.PositiveIntegerField(
        default=0,
        help_text="Earning user's Growth Level (direct qualifying sales) used for %",
    )
    percent = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0"))
    sale_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Qualifying sale / investment principal used for this calculation",
    )
    monthly_return_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Monthly return base (₹2,200) for growth/ROI commissions",
    )
    commission_month = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Month this recurring commission belongs to (1st of month)",
    )
    month_index = models.PositiveSmallIntegerField(
        default=0,
        help_text="Installment number 1–48 for monthly ROI / growth commission",
    )
    investment = models.ForeignKey(
        "investments.InvestmentContract",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commission_entries",
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    admin_charge_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    net_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Amount credited to the associate after admin charge.",
    )
    wallet_type = models.CharField(max_length=20, default="income")
    reference = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
        help_text="Transaction / sale reference (shared with wallet ledger)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREDITED,
        db_index=True,
    )
    narration = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["level", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["beneficiary", "level", "reference"],
                condition=~models.Q(reference=""),
                name="uniq_commission_beneficiary_level_reference",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.beneficiary_id} L{self.level} {self.amount} ({self.reference})"


class AdminCharge(BaseModel):
    """Company cut on a commission. Staff / finance only — never shown to associates."""

    class Kind(models.TextChoices):
        INCOME = "income", "Sale / Level Income"
        ROI = "roi", "ROI Level Income"
        REWARD = "reward", "Reward Income"

    associate = models.ForeignKey(
        Associate, on_delete=models.PROTECT, related_name="admin_charges"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    wallet_type = models.CharField(max_length=20)
    gross_amount = models.DecimalField(max_digits=16, decimal_places=2)
    charge_percent = models.DecimalField(max_digits=5, decimal_places=2)
    charge_amount = models.DecimalField(max_digits=16, decimal_places=2)
    net_amount = models.DecimalField(max_digits=16, decimal_places=2)
    reference = models.CharField(max_length=80, blank=True, db_index=True)
    narration = models.CharField(max_length=255, blank=True)
    commission_entry = models.ForeignKey(
        CommissionEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_charges",
    )
    ledger_entry = models.ForeignKey(
        "wallets.LedgerEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_charges",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind", "created_at"])]
        verbose_name = "Admin charge"
        verbose_name_plural = "Admin charges"

    def __str__(self) -> str:
        return f"{self.kind} {self.charge_amount} on {self.reference}"
