"""Level-based farmhouse commission constants (percentages stay in configuration DB)."""

from decimal import Decimal

from associates.models import PLATINUM_JOIN_AMOUNT

# One qualifying farmhouse sale = ₹2,20,000
FARHOUSE_SALE_AMOUNT = PLATINUM_JOIN_AMOUNT

# Hard cap aligned with LevelIncomePlan.max_levels default
MAX_COMMISSION_LEVELS = 5

# Default slabs (admin-editable via LevelIncomeSlab; seed syncs these)
DEFAULT_LEVEL_PERCENTS = (
    (1, Decimal("5.0000")),
    (2, Decimal("2.5000")),
    (3, Decimal("2.0000")),
    (4, Decimal("1.0000")),
    (5, Decimal("0.5000")),
)
