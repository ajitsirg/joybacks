from decimal import Decimal

from django.db import models
from django.utils import timezone

from associates.models import Associate
from core.models import BaseModel
from investments.constants import INVESTMENT_PRINCIPAL, MONTHLY_RETURN_AMOUNT, RETURN_MONTHS


class InvestmentContract(BaseModel):
    """
    One qualifying ₹2.2L unit → ₹2,200/month for 48 months.

    Created when personal investment business is applied (join / fund / deposit).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    associate = models.ForeignKey(
        Associate,
        on_delete=models.PROTECT,
        related_name="investment_contracts",
    )
    principal = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=INVESTMENT_PRINCIPAL,
    )
    monthly_return = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=MONTHLY_RETURN_AMOUNT,
    )
    months_total = models.PositiveSmallIntegerField(default=RETURN_MONTHS)
    months_paid = models.PositiveSmallIntegerField(default=0)
    unit_index = models.PositiveIntegerField(
        default=1,
        help_text="Nth farmhouse unit under the same source_reference",
    )
    source_reference = models.CharField(max_length=80, db_index=True)
    started_on = models.DateField(default=timezone.localdate)
    next_payout_on = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    last_payout_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "next_payout_on"]),
            models.Index(fields=["associate", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_reference", "unit_index"],
                name="uniq_investment_source_unit",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.associate.associate_id} {self.principal} "
            f"M{self.months_paid}/{self.months_total} ({self.status})"
        )

    @property
    def remaining_months(self) -> int:
        return max(0, int(self.months_total) - int(self.months_paid))
