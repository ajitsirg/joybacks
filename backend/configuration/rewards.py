"""Joy Adventure Resort — Reward Achievement slabs (9 levels, each from 0)."""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple


class RewardSlab(NamedTuple):
    level: int
    total: Decimal
    leg1: Decimal  # power / strongest leg (40%)
    leg2: Decimal
    leg3: Decimal
    reward: Decimal


# Each level is a full 0 → target window (not leftover from the previous slab).
# Level 1 starts at ₹25,00,000. Nine levels only — no Level 10.
REWARD_SLABS: tuple[RewardSlab, ...] = (
    RewardSlab(1, Decimal("2500000"), Decimal("1000000"), Decimal("750000"), Decimal("750000"), Decimal("75000")),
    RewardSlab(2, Decimal("5000000"), Decimal("2000000"), Decimal("1500000"), Decimal("1500000"), Decimal("150000")),
    RewardSlab(3, Decimal("10000000"), Decimal("4000000"), Decimal("3000000"), Decimal("3000000"), Decimal("400000")),
    RewardSlab(4, Decimal("20000000"), Decimal("8000000"), Decimal("6000000"), Decimal("6000000"), Decimal("1000000")),
    RewardSlab(5, Decimal("50000000"), Decimal("20000000"), Decimal("15000000"), Decimal("15000000"), Decimal("3000000")),
    RewardSlab(6, Decimal("100000000"), Decimal("40000000"), Decimal("30000000"), Decimal("30000000"), Decimal("6000000")),
    RewardSlab(7, Decimal("200000000"), Decimal("80000000"), Decimal("60000000"), Decimal("60000000"), Decimal("10000000")),
    RewardSlab(8, Decimal("500000000"), Decimal("200000000"), Decimal("150000000"), Decimal("150000000"), Decimal("25000000")),
    RewardSlab(9, Decimal("1000000000"), Decimal("400000000"), Decimal("300000000"), Decimal("300000000"), Decimal("50000000")),
)


def slab_for_level(level: int) -> RewardSlab | None:
    for slab in REWARD_SLABS:
        if slab.level == level:
            return slab
    return None


def active_slabs() -> tuple[RewardSlab, ...]:
    """Official 9-level table — never use stale Reward Master amounts."""
    return REWARD_SLABS


def official_reward_payload() -> list[dict]:
    """API/admin display payload. Amounts come only from REWARD_SLABS."""
    return [
        {
            "name": f"Level {slab.level}",
            "milestone_number": slab.level,
            "business_target": str(slab.total),
            "leg_business": str(slab.leg1),
            "leg1_target": str(slab.leg1),
            "leg2_target": str(slab.leg2),
            "leg3_target": str(slab.leg3),
            "reward_amount": str(slab.reward),
            "is_active": True,
            "sort_order": slab.level,
            "reward_type": "cash",
        }
        for slab in REWARD_SLABS
    ]


def sync_official_milestones() -> int:
    """Write the official table onto Reward Master (admin display only)."""
    from configuration.models import RewardMaster

    n = 0
    keep_names = {f"Level {slab.level}" for slab in REWARD_SLABS}
    for slab in REWARD_SLABS:
        RewardMaster.objects.update_or_create(
            name=f"Level {slab.level}",
            defaults={
                "milestone_number": slab.level,
                "business_target": slab.total,
                "leg_business": slab.leg1,
                "leg1_target": slab.leg1,
                "leg2_target": slab.leg2,
                "leg3_target": slab.leg3,
                "reward_amount": slab.reward,
                "sort_order": slab.level,
                "is_active": True,
                "reward_type": "cash",
                "description": (
                    f"Level {slab.level}: 0 → ₹{slab.total} · "
                    f"Leg1 ₹{slab.leg1} · Leg2 ₹{slab.leg2} · Leg3 ₹{slab.leg3} "
                    f"→ ₹{slab.reward}"
                ),
            },
        )
        n += 1
    RewardMaster.objects.exclude(name__in=keep_names).filter(name__startswith="Level ").update(
        is_active=False
    )
    return n
