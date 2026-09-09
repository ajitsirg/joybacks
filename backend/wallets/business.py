"""Apply personal / team business and level income after a fund investment."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from associates.models import Associate
from commissions.services import CommissionEngine


@transaction.atomic
def apply_investment_business(
    *,
    associate: Associate,
    amount: Decimal,
    reference: str,
) -> None:
    """Mirror deposit-approve math: personal + team business, ranks, level income."""
    if amount <= 0:
        raise ValueError("Amount must be positive")

    assoc = Associate.objects.select_for_update().get(pk=associate.pk)
    if assoc.status in {
        Associate.Status.PENDING,
        Associate.Status.REJECTED,
        Associate.Status.BLOCKED,
    }:
        raise ValueError(
            "Associate must be approved (Inactive/Active) before fund investment can be applied"
        )

    assoc.personal_business += amount
    assoc.total_business += amount
    assoc.sync_flag_color(save=False)
    assoc.sync_rank_levels(save=False)
    assoc.save(
        update_fields=[
            "personal_business",
            "total_business",
            "flag_color",
            "earning_level",
            "earning_level_name",
            "performance_level",
            "performance_level_name",
            "updated_at",
        ]
    )
    assoc.sync_status_from_investment(save=True)

    from genealogy.services import GenealogyService

    for link in GenealogyService.upline(assoc):
        ancestor = Associate.objects.select_for_update().get(pk=link.ancestor_id)
        ancestor.total_business += amount
        ancestor.sync_rank_levels(save=False)
        ancestor.save(
            update_fields=[
                "total_business",
                "earning_level",
                "earning_level_name",
                "performance_level",
                "performance_level_name",
                "updated_at",
            ]
        )

    if assoc.sponsor_id:
        sponsor = Associate.objects.select_for_update().get(pk=assoc.sponsor_id)
        sponsor.direct_active_count = sponsor.directs.filter(
            status=Associate.Status.ACTIVE, is_deleted=False
        ).count()
        sponsor.sync_performance_level(save=False)
        sponsor.save(
            update_fields=[
                "direct_active_count",
                "performance_level",
                "performance_level_name",
                "updated_at",
            ]
        )

    CommissionEngine.distribute_level_income(
        source_associate=assoc,
        amount=amount,
        reference=reference,
    )

    # Re-sync rewards after every upline total is committed so L1 ₹75,000
    # credits as soon as three legs qualify (10L + 7.5L + 7.5L).
    assoc.refresh_from_db()
    assoc.sync_earning_level(save=True)
    for link in GenealogyService.upline(assoc):
        ancestor = Associate.objects.get(pk=link.ancestor_id)
        ancestor.sync_earning_level(save=True)

    from investments.services import create_investment_contracts

    create_investment_contracts(
        associate=assoc,
        amount=amount,
        reference=reference,
    )
