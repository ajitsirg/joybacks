"""Performance Reward Achievement: 3 legs, 9 levels from 0, pay once each."""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from configuration.rewards import REWARD_SLABS, RewardSlab


def first_line_members(associate) -> list:
    """Eligible directs: sponsor children union genealogy children."""
    from associates.models import Associate
    from genealogy.models import GenealogyNode

    by_id: dict = {}
    for child in Associate.objects.filter(sponsor=associate, is_deleted=False):
        by_id[child.pk] = child

    node = GenealogyNode.objects.filter(associate=associate).first()
    if node:
        kids = GenealogyNode.objects.filter(parent=node).select_related("associate", "associate__user")
        for kn in kids:
            child = kn.associate
            if not child or getattr(child, "is_deleted", False):
                continue
            by_id[child.pk] = child
    return list(by_id.values())


def first_line_volumes(associate) -> list[Decimal]:
    return [qualifying_business(m) for m in first_line_members(associate)]


def qualifying_business(member) -> Decimal:
    """Downstream + personal volume already stored on the associate."""
    if member is None:
        return Decimal("0")
    return Decimal(member.total_business or 0)


def _member_label(member) -> str:
    if member is None:
        return ""
    user = getattr(member, "user", None)
    name = ""
    if user:
        name = (user.get_full_name() or user.username or "").strip()
    return name


def resolve_reward_legs(associate, *, persist: bool = True) -> list[dict]:
    """
    Three performance legs.

    Locked slots stay on the chosen member. Otherwise the engine keeps the
    current top 3 first-line performers by qualifying business.
    """
    from associates.models import RewardLegAssignment

    members = first_line_members(associate)
    locked = {
        int(row.slot): row
        for row in RewardLegAssignment.objects.filter(owner=associate, locked=True, is_deleted=False)
        if int(row.slot) in (1, 2, 3)
    }
    use_locked = len(locked) == 3

    if use_locked:
        chosen: list = []
        for slot in (1, 2, 3):
            row = locked[slot]
            performer = row.performer
            if performer and getattr(performer, "is_deleted", False):
                performer = None
            chosen.append((slot, performer, True))
    else:
        ranked = sorted(
            members,
            key=lambda m: (qualifying_business(m), m.associate_id or ""),
            reverse=True,
        )
        top = ranked[:3]
        while len(top) < 3:
            top.append(None)
        chosen = [(i, p, False) for i, p in enumerate(top, start=1)]
        if persist:
            _persist_auto_legs(associate, chosen)

    out = []
    for slot, performer, locked_flag in chosen:
        out.append(
            {
                "slot": slot,
                "associate_id": performer.associate_id if performer else "",
                "name": _member_label(performer),
                "business": qualifying_business(performer),
                "locked": locked_flag,
            }
        )
    return out


def _persist_auto_legs(associate, chosen: list) -> None:
    from associates.models import RewardLegAssignment

    for slot, performer, _locked in chosen:
        row, _ = RewardLegAssignment.objects.get_or_create(
            owner=associate,
            slot=slot,
            defaults={"performer": performer, "locked": False},
        )
        if row.locked:
            continue
        if row.performer_id != (performer.pk if performer else None):
            row.performer = performer
            row.save(update_fields=["performer", "updated_at"])


def set_reward_legs(associate, *, performer_ids: list[str] | None = None, auto: bool = False) -> list[dict]:
    """Pin three first-line members as legs, or return to automatic top-3."""
    from associates.models import RewardLegAssignment

    if auto or not performer_ids:
        RewardLegAssignment.objects.filter(owner=associate).update(locked=False)
        return resolve_reward_legs(associate, persist=True)

    ids = [str(x).strip() for x in performer_ids if str(x).strip()]
    if len(ids) != 3 or len(set(x.lower() for x in ids)) != 3:
        raise ValueError("Select exactly 3 different first-line members for Leg 1, 2 and 3.")

    members = first_line_members(associate)
    by_code = {m.associate_id.lower(): m for m in members}
    picked = []
    for code in ids:
        member = by_code.get(code.lower())
        if not member:
            raise ValueError(f"{code} is not in your first-line network.")
        picked.append(member)

    for slot, member in enumerate(picked, start=1):
        row, _ = RewardLegAssignment.objects.get_or_create(
            owner=associate,
            slot=slot,
            defaults={"performer": member, "locked": True},
        )
        row.performer = member
        row.locked = True
        row.save(update_fields=["performer", "locked", "updated_at"])
    return resolve_reward_legs(associate, persist=False)


def ranked_leg_business(associate) -> tuple[Decimal, Decimal, Decimal]:
    snap = reward_snapshot(associate)
    return snap["leg1"], snap["leg2"], snap["leg3"]


def qualifies(slab: RewardSlab, *, total: Decimal, leg1: Decimal, leg2: Decimal, leg3: Decimal) -> bool:
    return (
        Decimal(total or 0) >= slab.total
        and Decimal(leg1 or 0) >= slab.leg1
        and Decimal(leg2 or 0) >= slab.leg2
        and Decimal(leg3 or 0) >= slab.leg3
    )


def compute_reward_level(
    *,
    total_business: Decimal,
    leg1: Decimal,
    leg2: Decimal,
    leg3: Decimal,
) -> tuple[int, str]:
    """Highest milestone where total + each of the 3 legs meet the configured rupees."""
    level = 0
    name = "No level"
    for slab in REWARD_SLABS:
        if qualifies(slab, total=total_business, leg1=leg1, leg2=leg2, leg3=leg3):
            level = slab.level
            name = f"Level {slab.level}"
    return level, name


def reward_snapshot(associate) -> dict:
    """Live 3-leg progress. Total Reward Business = Leg1 + Leg2 + Leg3 only."""
    legs = resolve_reward_legs(associate)
    while len(legs) < 3:
        legs.append(
            {"slot": len(legs) + 1, "associate_id": "", "name": "", "business": Decimal("0"), "locked": False}
        )
    leg1 = Decimal(legs[0]["business"] or 0)
    leg2 = Decimal(legs[1]["business"] or 0)
    leg3 = Decimal(legs[2]["business"] or 0)
    total = leg1 + leg2 + leg3
    level, name = compute_reward_level(total_business=total, leg1=leg1, leg2=leg2, leg3=leg3)
    slabs = list(REWARD_SLABS)
    next_slab = None
    for slab in slabs:
        if slab.level == level + 1:
            next_slab = slab
            break
    target = next_slab or (slabs[0] if level == 0 and slabs else None)
    milestones = []
    first_pending: int | None = None
    for slab in slabs:
        ok = qualifies(slab, total=total, leg1=leg1, leg2=leg2, leg3=leg3)
        if ok:
            status = "achieved"
        elif first_pending is None:
            status = "pending"
            first_pending = slab.level
        else:
            status = "locked"
        milestones.append(
            {
                "sno": slab.level,
                "total": slab.total,
                "leg1": slab.leg1,
                "leg2": slab.leg2,
                "leg3": slab.leg3,
                "reward": slab.reward,
                "status": status,
                "leg1_ok": Decimal(leg1 or 0) >= slab.leg1,
                "leg2_ok": Decimal(leg2 or 0) >= slab.leg2,
                "leg3_ok": Decimal(leg3 or 0) >= slab.leg3,
                "total_ok": Decimal(total or 0) >= slab.total,
                "remaining_total": max(Decimal("0"), slab.total - total),
                "remaining_leg1": max(Decimal("0"), slab.leg1 - leg1),
                "remaining_leg2": max(Decimal("0"), slab.leg2 - leg2),
                "remaining_leg3": max(Decimal("0"), slab.leg3 - leg3),
            }
        )
    return {
        "total": total,
        "leg1": leg1,
        "leg2": leg2,
        "leg3": leg3,
        "level": level,
        "name": name,
        "legs": legs,
        "current_milestone": level,
        "next_milestone": next_slab.level if next_slab else None,
        "remaining_total": max(Decimal("0"), target.total - total) if target else Decimal("0"),
        "remaining_leg1": max(Decimal("0"), target.leg1 - leg1) if target else Decimal("0"),
        "remaining_leg2": max(Decimal("0"), target.leg2 - leg2) if target else Decimal("0"),
        "remaining_leg3": max(Decimal("0"), target.leg3 - leg3) if target else Decimal("0"),
        "next_targets": (
            {
                "sno": target.level,
                "total": target.total,
                "leg1": target.leg1,
                "leg2": target.leg2,
                "leg3": target.leg3,
                "reward": target.reward,
            }
            if target
            else None
        ),
        "milestones": milestones,
        "auto": not any(leg.get("locked") for leg in legs),
        "candidates": [
            {
                "associate_id": m.associate_id,
                "name": _member_label(m),
                "business": qualifying_business(m),
            }
            for m in sorted(first_line_members(associate), key=lambda x: qualifying_business(x), reverse=True)
        ],
    }


def compute_reward_level_for(associate) -> tuple[int, str]:
    snap = reward_snapshot(associate)
    return snap["level"], snap["name"]


def _money(v) -> str:
    return str(v)


def progress_api_dict(associate) -> dict:
    snap = reward_snapshot(associate)
    return {
        "total": _money(snap["total"]),
        "leg1": _money(snap["leg1"]),
        "leg2": _money(snap["leg2"]),
        "leg3": _money(snap["leg3"]),
        "level": snap["level"],
        "name": snap["name"],
        "current_milestone": snap["current_milestone"],
        "next_milestone": snap["next_milestone"],
        "remaining_total": _money(snap["remaining_total"]),
        "remaining_leg1": _money(snap["remaining_leg1"]),
        "remaining_leg2": _money(snap["remaining_leg2"]),
        "remaining_leg3": _money(snap["remaining_leg3"]),
        "auto": snap["auto"],
        "legs": [
            {
                "slot": leg["slot"],
                "associate_id": leg["associate_id"],
                "name": leg["name"],
                "business": _money(leg["business"]),
                "locked": leg["locked"],
            }
            for leg in snap["legs"]
        ],
        "next_targets": (
            {k: _money(v) if k != "sno" else v for k, v in snap["next_targets"].items()}
            if snap["next_targets"]
            else None
        ),
        "milestones": [
            {
                **{
                    k: (
                        v
                        if k in ("sno", "status", "leg1_ok", "leg2_ok", "leg3_ok", "total_ok")
                        else _money(v)
                    )
                    for k, v in row.items()
                },
            }
            for row in snap["milestones"]
        ],
        "next_overall_status": (
            "achieved"
            if snap["next_targets"]
            and all(
                Decimal(snap[k] or 0) >= Decimal(snap["next_targets"][k] or 0)
                for k in ("leg1", "leg2", "leg3", "total")
            )
            else "pending"
        ),
        "candidates": [
            {
                "associate_id": c["associate_id"],
                "name": c["name"],
                "business": _money(c["business"]),
            }
            for c in snap["candidates"]
        ],
    }


def milestone_refs(associate_id: str, milestone: int) -> list[str]:
    """Current, adjustment, and legacy references for the same user + milestone."""
    aid = str(associate_id)
    n = int(milestone)
    return [
        f"REWARD-M{n}-{aid}",
        f"REWARD-M{n}-ADJ-{aid}",
        f"REWARD-L{n}-{aid}",
        f"REWARD-M{n}",
        f"REWARD-L{n}",
    ]


def _credited_milestone_total(*, associate, milestone: int) -> Decimal:
    """Sum already paid for this user + milestone. Keep legacy L-rows; never double-pay."""
    from commissions.models import CommissionEntry, CommissionRun

    n = int(milestone)
    aid = associate.associate_id
    qs = (
        CommissionEntry.objects.filter(beneficiary=associate, is_deleted=False)
        .exclude(status=CommissionEntry.Status.VOIDED)
        .filter(
            Q(run__run_type=CommissionRun.RunType.REWARD, level=n)
            | Q(reference__iexact=f"REWARD-M{n}-{aid}")
            | Q(reference__iexact=f"REWARD-M{n}-ADJ-{aid}")
            | Q(reference__iexact=f"REWARD-L{n}-{aid}")
            | Q(reference__iexact=f"REWARD-M{n}")
            | Q(reference__iexact=f"REWARD-L{n}")
            | Q(reference__istartswith=f"REWARD-M{n}-{aid}")
            | Q(reference__istartswith=f"REWARD-L{n}-{aid}")
            | Q(reference__istartswith=f"REWARD-M{n}-ADJ-")
        )
    )
    return qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def pay_unlocked_rewards(*, associate, old_level: int, new_level: int) -> int:
    """Credit official milestone cash once per user + milestone (idempotent)."""
    if new_level <= old_level:
        return 0
    from associates.models import RewardAchievement
    from commissions.models import CommissionEntry, CommissionRun
    from wallets.models import Wallet
    from wallets.services import WalletService

    snap = reward_snapshot(associate)
    paid = 0
    WalletService.ensure_wallets(associate)
    for slab in REWARD_SLABS:
        if slab.level <= old_level or slab.level > new_level:
            continue
        if not qualifies(
            slab, total=snap["total"], leg1=snap["leg1"], leg2=snap["leg2"], leg3=snap["leg3"]
        ):
            continue
        already = _credited_milestone_total(associate=associate, milestone=slab.level)
        due = Decimal(slab.reward)
        if already >= due:
            continue
        payout = (due - already).quantize(Decimal("0.01"))
        aid = associate.associate_id
        ref = f"REWARD-M{slab.level}-{aid}" if already == 0 else f"REWARD-M{slab.level}-ADJ-{aid}"
        run = CommissionRun.objects.create(
            run_type=CommissionRun.RunType.REWARD,
            status=CommissionRun.Status.PENDING,
            source_reference=ref,
            source_amount=payout,
            notes=f"Reward Milestone {slab.level} ₹{due}"
            + (f" (top-up ₹{payout} after prior ₹{already})" if already else ""),
        )
        try:
            with transaction.atomic():
                entry = CommissionEntry.objects.create(
                    run=run,
                    beneficiary=associate,
                    source_associate=associate,
                    level=slab.level,
                    percent=Decimal("0"),
                    sale_amount=slab.total,
                    amount=payout,
                    wallet_type=Wallet.WalletType.REWARD,
                    reference=ref,
                    status=CommissionEntry.Status.CREDITED,
                    narration=(
                        f"Reward Milestone {slab.level}: ₹{payout}"
                        + (f" top-up to ₹{due}" if already else f" of ₹{due}")
                        + f" (total ₹{slab.total} · L1 ₹{slab.leg1} · L2 ₹{slab.leg2} · L3 ₹{slab.leg3})"
                    ),
                )
                from commissions.charges import credit_commission

                credit_commission(
                    associate=associate,
                    wallet_type=Wallet.WalletType.REWARD,
                    gross=payout,
                    reference=ref,
                    narration=(
                        f"Reward Milestone {slab.level}"
                        + (f" top-up ₹{payout}" if already else "")
                    ),
                    kind="reward",
                    commission_entry=entry,
                    meta={
                        "milestone": slab.level,
                        "total": str(slab.total),
                        "reward": str(due),
                        "credited_now": str(payout),
                    },
                )
                achievement, created = RewardAchievement.objects.get_or_create(
                    associate=associate,
                    milestone=slab.level,
                    defaults={
                        "total_business": snap["total"],
                        "leg1_business": snap["leg1"],
                        "leg2_business": snap["leg2"],
                        "leg3_business": snap["leg3"],
                        "reward_amount": slab.reward,
                        "credited_at": timezone.now(),
                        "status": RewardAchievement.Status.CREDITED,
                        "reference": ref,
                    },
                )
                if not created and achievement.reward_amount != slab.reward:
                    achievement.reward_amount = slab.reward
                    achievement.save(update_fields=["reward_amount", "updated_at"])
        except IntegrityError:
            run.status = CommissionRun.Status.COMPLETED
            run.notes = (run.notes or "") + "; duplicate skipped"
            run.save(update_fields=["status", "notes", "updated_at"])
            continue
        run.status = CommissionRun.Status.COMPLETED
        run.save(update_fields=["status", "updated_at"])
        paid += 1
    return paid
