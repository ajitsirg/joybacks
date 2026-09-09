"""ROI-on-ROI calculation helpers — level % always on base ROI, never on investment."""

from __future__ import annotations

from decimal import Decimal

from configuration.repository import ConfigRepository
from investments.constants import DEFAULT_GROWTH_PERCENTS, INVESTMENT_PRINCIPAL, MONTHLY_RETURN_AMOUNT


def roi_rate_percent() -> Decimal:
    """Monthly ROI rate from admin ROI plan (default 1% → ₹2,200 on ₹2.2L)."""
    plan = ConfigRepository.active_roi_plan()
    if plan and plan.percent is not None:
        return Decimal(plan.percent)
    return Decimal("1.0000")


def base_roi_amount(principal: Decimal | None = None) -> Decimal:
    """
    Base ROI = Investment × ROI Rate / 100.

    Example: ₹2,20,000 × 1% = ₹2,200
    """
    principal = Decimal(principal or INVESTMENT_PRINCIPAL)
    return (principal * roi_rate_percent() / Decimal("100")).quantize(Decimal("0.01"))


def network_level_percent(network_level: int) -> Decimal:
    """Level N upline % from Performance Income plan (5 / 2.5 / 2 / … / 0.25)."""
    if network_level < 1:
        return Decimal("0")
    pct = ConfigRepository.performance_percent(network_level)
    if pct > 0:
        return pct
    return dict(DEFAULT_GROWTH_PERCENTS).get(network_level, Decimal("0"))


def roi_level_income(*, base_roi: Decimal, network_level: int) -> Decimal:
    """
    ROI-on-ROI: Level Income = Base ROI × Level Percentage / 100.

    NOT investment × level % — always applied to the eligible ROI amount.
    """
    pct = network_level_percent(network_level)
    if pct <= 0 or base_roi <= 0:
        return Decimal("0.00")
    return (Decimal(base_roi) * pct / Decimal("100")).quantize(Decimal("0.01"))


def default_monthly_return() -> Decimal:
    """Fallback monthly return when plan unavailable."""
    computed = base_roi_amount(INVESTMENT_PRINCIPAL)
    return computed if computed > 0 else MONTHLY_RETURN_AMOUNT
