"""Create the real Ganpati Maharaj → Joy Club → … → Amar Sinh Jat line."""

from __future__ import annotations

from collections import deque
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from associates.models import Associate, generate_referral_code, tier_from_amount
from configuration.models import GenealogySettings
from configuration.repository import ConfigRepository
from genealogy.models import GenealogyClosure, GenealogyNode
from genealogy.services import GenealogyService
from wallets.services import WalletService

User = get_user_model()

PASSWORD = "Joyclub@123"
JOIN_AMOUNT = Decimal("0")

# (associate_id, first_name, last_name, mobile, email)
# Chain order: each row is sponsored by the previous (first by JOYSIDDHI01)
LINE = [
    ("JOYSIDDHI01", "श्री सिद्धिविनायक", "गणपति महाराज", "9000888801", "siddhivinayak@joyclubs.in"),
    ("JOY00000001", "Joy", "Club", "9000000001", "root@joyclub.associate"),
    ("JOYCLUB01", "Joy", "Club 1", "9000000002", "joyclub01@joyclubs.in"),
    ("JOYCLUB02", "Joy", "Club 2", "9000000003", "joyclub02@joyclubs.in"),
    ("JOYCLUB03", "Joy", "Club 3", "9000000004", "joyclub03@joyclubs.in"),
    ("JOY9119119351", "Amar", "Sinh Jat", "9119119351", "amar.sinh.jat@joyclubs.in"),
]


class Command(BaseCommand):
    help = "Ensure Ganpati Maharaj downline: Joy Club → Club 1 → 2 → 3 → Amar Sinh Jat"

    def handle(self, *args, **options):
        with transaction.atomic():
            created: list[Associate] = []
            sponsor: Associate | None = None
            for aid, first, last, mobile, email in LINE:
                assoc = self._upsert(
                    associate_id=aid,
                    first=first,
                    last=last,
                    mobile=mobile,
                    email=email,
                    sponsor=sponsor,
                    password=PASSWORD,
                    is_root=sponsor is None,
                )
                WalletService.ensure_wallets(assoc)
                created.append(assoc)
                sponsor = assoc

            self._rebuild_genealogy(created[0])

        self.stdout.write(self.style.SUCCESS("Ganpati line ready:"))
        for a in created:
            name = a.user.get_full_name()
            sp = a.sponsor_associate_id or "(root)"
            self.stdout.write(f"  {a.associate_id} | {name} | mobile {a.mobile} | sponsor {sp} | pass {PASSWORD}")

    def _upsert(
        self,
        *,
        associate_id: str,
        first: str,
        last: str,
        mobile: str,
        email: str,
        sponsor: Associate | None,
        password: str,
        is_root: bool,
    ) -> Associate:
        tier, flag = tier_from_amount(JOIN_AMOUNT)
        user = User.objects.filter(username__iexact=associate_id).first()
        if not user:
            user = User.objects.filter(email__iexact=email).first()
        if user:
            user.username = associate_id
            user.email = email
            user.first_name = first
            user.last_name = last
            user.phone = mobile
            user.user_type = "associate"
            user.is_active = True
            # Keep staff flags on company root if already staff — but Joy Club root is associate
            if associate_id != "JOY00000001":
                user.is_staff = False
            user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                username=associate_id,
                first_name=first,
                last_name=last,
                phone=mobile,
                user_type="associate",
            )

        assoc = Associate.all_objects.filter(associate_id__iexact=associate_id).first()
        if not assoc:
            assoc = Associate.all_objects.filter(user=user).first()

        fields = dict(
            user=user,
            associate_id=associate_id,
            mobile=mobile,
            sponsor=None if is_root else sponsor,
            sponsor_associate_id="" if is_root else sponsor.associate_id,
            lead_reference="" if is_root else sponsor.associate_id,
            status=Associate.Status.ACTIVE,
            activated_at=timezone.now(),
            kyc_verified=True,
            join_amount=JOIN_AMOUNT,
            card_tier=tier,
            flag_color=flag,
            city="Jaipur",
            state="Rajasthan",
            country="India",
            is_deleted=False,
            deleted_at=None,
            login_password=password,
        )
        if assoc:
            for key, value in fields.items():
                setattr(assoc, key, value)
            if not assoc.referral_code:
                assoc.referral_code = generate_referral_code()
            assoc.save()
        else:
            assoc = Associate.objects.create(**fields, referral_code=generate_referral_code())
        return assoc

    def _rebuild_genealogy(self, leader: Associate) -> None:
        gs = ConfigRepository.genealogy()
        old_mode, old_max = gs.leg_mode, gs.max_legs
        gs.leg_mode = GenealogySettings.LegMode.UNLIMITED
        gs.max_legs = 0
        gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
        try:
            GenealogyClosure.objects.all().delete()
            GenealogyNode.all_objects.update(parent=None)
            GenealogyNode.all_objects.all().delete()

            roots = list(
                Associate.objects.filter(sponsor__isnull=True, is_deleted=False).order_by("created_at")
            )
            if leader not in roots:
                roots.insert(0, leader)
            for root in roots:
                GenealogyService.ensure_root(root)

            queue: deque[Associate] = deque(roots)
            seen = {r.pk for r in roots}
            while queue:
                parent = queue.popleft()
                children = list(
                    Associate.objects.filter(sponsor=parent, is_deleted=False).order_by("created_at")
                )
                for child in children:
                    if child.pk in seen:
                        continue
                    GenealogyService.attach_under_sponsor(child, parent)
                    seen.add(child.pk)
                    queue.append(child)

            for a in Associate.objects.filter(is_deleted=False):
                a.direct_count = a.directs.filter(is_deleted=False).count()
                a.direct_active_count = a.directs.filter(
                    status=Associate.Status.ACTIVE, is_deleted=False
                ).count()
                a.save(update_fields=["direct_count", "direct_active_count", "updated_at"])
        finally:
            gs.leg_mode = old_mode
            gs.max_legs = old_max
            gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
