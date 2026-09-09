"""Repository accessors for runtime configuration (never hardcode)."""

from __future__ import annotations

from decimal import Decimal

from configuration.models import (
    CompanySettings,
    GenealogySettings,
    LevelIncomePlan,
    LevelIncomeSlab,
    PerformanceIncomePlan,
    PerformanceIncomeSlab,
    ROIPlan,
    RewardMaster,
    WithdrawalSettings,
)


class ConfigRepository:
    @staticmethod
    def company() -> CompanySettings:
        return CompanySettings.current()

    @staticmethod
    def genealogy() -> GenealogySettings:
        obj = GenealogySettings.objects.filter(is_active=True).order_by("created_at").first()
        if obj:
            return obj
        return GenealogySettings.objects.create()

    @staticmethod
    def withdrawal() -> WithdrawalSettings:
        obj = WithdrawalSettings.objects.filter(is_active=True).order_by("created_at").first()
        if obj:
            return obj
        return WithdrawalSettings.objects.create()

    @staticmethod
    def active_level_plan() -> LevelIncomePlan | None:
        qs = LevelIncomePlan.objects.filter(is_active=True).prefetch_related("slabs")
        return qs.filter(code="direct-level").first() or qs.order_by("created_at").first()

    @staticmethod
    def level_percent(level: int) -> Decimal:
        from commissions.constants import DEFAULT_LEVEL_PERCENTS

        plan = ConfigRepository.active_level_plan()
        if plan:
            slab = plan.slabs.filter(level=level, is_active=True).first()
            if slab and Decimal(slab.percent or 0) > 0:
                return Decimal(slab.percent)
        return dict(DEFAULT_LEVEL_PERCENTS).get(int(level), Decimal("0"))

    @staticmethod
    def active_performance_plan() -> PerformanceIncomePlan | None:
        qs = PerformanceIncomePlan.objects.filter(is_active=True).prefetch_related("slabs")
        return qs.filter(code="performance-10").first() or qs.order_by("created_at").first()

    @staticmethod
    def performance_percent(level: int) -> Decimal:
        from investments.constants import DEFAULT_GROWTH_PERCENTS

        plan = ConfigRepository.active_performance_plan()
        if plan:
            slab = plan.slabs.filter(level=level, is_active=True).first()
            if slab and Decimal(slab.percent or 0) > 0:
                return Decimal(slab.percent)
        return dict(DEFAULT_GROWTH_PERCENTS).get(int(level), Decimal("0"))

    @staticmethod
    def performance_required_directs(level: int) -> int:
        """Qualified directs required to unlock ROI-on-ROI depth `level`."""
        plan = ConfigRepository.active_performance_plan()
        if plan:
            slab = plan.slabs.filter(level=level, is_active=True).first()
            if slab is not None:
                raw = int(slab.required_directs or 0)
                return raw if raw > 0 else int(level)
        return int(level)

    @staticmethod
    def active_roi_plan() -> ROIPlan | None:
        qs = ROIPlan.objects.filter(is_active=True)
        return qs.filter(code="monthly-roi-48").first() or qs.order_by("created_at").first()

    @staticmethod
    def active_rewards():
        from configuration.rewards import sync_official_milestones

        sync_official_milestones()
        return RewardMaster.objects.filter(is_active=True).order_by("milestone_number", "sort_order")
