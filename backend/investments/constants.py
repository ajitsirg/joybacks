"""Growth-level monthly ROI constants (₹2.2L investment → ₹2,200 × 48 months)."""

from decimal import Decimal

from associates.models import PLATINUM_JOIN_AMOUNT

INVESTMENT_PRINCIPAL = PLATINUM_JOIN_AMOUNT  # ₹2,20,000
MONTHLY_RETURN_AMOUNT = Decimal("2200.00")
RETURN_MONTHS = 48
MAX_GROWTH_LEVELS = 10

# Growth Level % by direct qualifying sales (admin PerformanceIncomePlan is source of truth)
DEFAULT_GROWTH_PERCENTS = (
    (1, Decimal("5.0000")),
    (2, Decimal("2.5000")),
    (3, Decimal("2.0000")),
    (4, Decimal("2.0000")),
    (5, Decimal("1.0000")),
    (6, Decimal("1.0000")),
    (7, Decimal("0.5000")),
    (8, Decimal("0.5000")),
    (9, Decimal("0.2500")),
    (10, Decimal("0.2500")),
)
