"""Create top associate श्री सिद्धिविनायक गणपति महाराज and place all others under them."""

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

ASSOCIATE_ID = "JOYSIDDHI01"
PASSWORD = "Siddhi@1234"
MOBILE = "9000888801"
EMAIL = "siddhivinayak@joyclubs.in"
FIRST_NAME = "श्री सिद्धिविनायक"
LAST_NAME = "गणपति महाराज"
JOIN_AMOUNT = Decimal("220000")


class Command(BaseCommand):
    help = "Ensure JOYSIDDHI01 (श्री सिद्धिविनायक गणपति महाराज) as top root with all associates under"

    def handle(self, *args, **options):
        with transaction.atomic():
            leader = self._upsert_leader()
            WalletService.ensure_wallets(leader)

            # Every previous top-level root becomes a direct under the new leader
            previous_roots = list(
                Associate.objects.filter(sponsor__isnull=True, is_deleted=False).exclude(pk=leader.pk)
            )
            for root in previous_roots:
                root.sponsor = leader
                root.sponsor_associate_id = leader.associate_id
                if not root.lead_reference:
                    root.lead_reference = leader.associate_id
                root.save(update_fields=["sponsor", "sponsor_associate_id", "lead_reference", "updated_at"])
                self.stdout.write(f"Reparented previous root {root.associate_id} → {ASSOCIATE_ID}")

            self._rebuild_genealogy(leader)

            leader.direct_count = leader.directs.filter(is_deleted=False).count()
            leader.direct_active_count = leader.directs.filter(
                status=Associate.Status.ACTIVE, is_deleted=False
            ).count()
            leader.save(update_fields=["direct_count", "direct_active_count", "updated_at"])

        total = Associate.objects.filter(is_deleted=False).count()
        under = GenealogyClosure.objects.filter(ancestor=leader, depth__gt=0).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"READY | id={ASSOCIATE_ID} | password={PASSWORD} | "
                f"name={FIRST_NAME} {LAST_NAME} | directs={leader.direct_count} | "
                f"downline={under} | total_associates={total}"
            )
        )

    def _upsert_leader(self) -> Associate:
        tier, flag = tier_from_amount(JOIN_AMOUNT)
        user = User.objects.filter(username__iexact=ASSOCIATE_ID).first()
        if not user:
            user = User.objects.filter(email__iexact=EMAIL).first()
        if user:
            user.username = ASSOCIATE_ID
            user.email = EMAIL
            user.first_name = FIRST_NAME
            user.last_name = LAST_NAME
            user.phone = MOBILE
            user.user_type = "associate"
            user.is_active = True
            user.is_staff = False
            user.set_password(PASSWORD)
            user.save()
        else:
            user = User.objects.create_user(
                email=EMAIL,
                password=PASSWORD,
                username=ASSOCIATE_ID,
                first_name=FIRST_NAME,
                last_name=LAST_NAME,
                phone=MOBILE,
                user_type="associate",
            )

        assoc = Associate.objects.filter(associate_id__iexact=ASSOCIATE_ID).first()
        if not assoc:
            assoc = Associate.objects.filter(user=user).first()

        fields = dict(
            user=user,
            associate_id=ASSOCIATE_ID,
            mobile=MOBILE,
            sponsor=None,
            sponsor_associate_id="",
            lead_reference="",
            status=Associate.Status.ACTIVE,
            activated_at=timezone.now(),
            kyc_verified=True,
            join_amount=JOIN_AMOUNT,
            card_tier=tier,
            flag_color=flag,
            city="Mumbai",
            state="Maharashtra",
            country="India",
            can_view_admin_history=True,
            can_view_reward_achievers=True,
            login_password=PASSWORD,
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
            # parent is PROTECT — clear links before wipe
            GenealogyNode.all_objects.update(parent=None)
            GenealogyNode.all_objects.all().delete()

            roots = list(Associate.objects.filter(sponsor__isnull=True, is_deleted=False).order_by("created_at"))
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
        finally:
            gs.leg_mode = old_mode
            gs.max_legs = old_max
            gs.save(update_fields=["leg_mode", "max_legs", "updated_at"])
