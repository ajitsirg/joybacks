"""25 dummy IDs under live associate JOY70000015.

Create only JOYDM15U01..U25. No farmhouse investment, no commissions.
When asked to delete: --inactivate (status inactive, not hard-delete).
Never touches JOY70000015, JOYSIDDHI01, or JOY00000001.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from associates.models import Associate, generate_referral_code
from genealogy.models import GenealogyNode
from genealogy.services import GenealogyService
from wallets.services import WalletService

User = get_user_model()

SPONSOR_ID = "JOY7000000015"
SPONSOR_ALIASES = {"JOY70000015": SPONSOR_ID, "JOY7000000015": SPONSOR_ID}
PREFIX = "JOYDM15"
PASSWORD = "dummy1234"
PROTECTED = frozenset({"JOYSIDDHI01", "JOY00000001", SPONSOR_ID})


def dummy_ids() -> list[str]:
    return [f"{PREFIX}U{i:02d}" for i in range(1, 26)]


def _is_dummy(assoc: Associate) -> bool:
    aid = (assoc.associate_id or "").upper()
    email = (getattr(assoc.user, "email", "") or "").lower()
    return aid.startswith(PREFIX) or (
        email.endswith("@joyclub.dummy") and aid.startswith("JOYDM15")
    )


class Command(BaseCommand):
    help = "Create or inactivate 25 dummy IDs (JOYDM15U*) under JOY70000015"

    def add_arguments(self, parser):
        parser.add_argument(
            "--inactivate",
            action="store_true",
            help="Mark JOYDM15U* dummy IDs inactive (no hard delete)",
        )
        parser.add_argument(
            "--sponsor",
            default=SPONSOR_ID,
            help=f"Sponsor associate ID (default {SPONSOR_ID})",
        )

    def handle(self, *args, **options):
        sponsor_id = str(options["sponsor"] or SPONSOR_ID).strip().upper()
        sponsor_id = SPONSOR_ALIASES.get(sponsor_id, sponsor_id)
        if sponsor_id in {"JOYSIDDHI01", "JOY00000001"}:
            raise SystemExit("Refusing to attach dummy IDs under a protected associate")
        if options["inactivate"]:
            self._inactivate()
            return
        self._create(sponsor_id)

    @transaction.atomic
    def _inactivate(self) -> None:
        qs = Associate.objects.filter(associate_id__startswith=PREFIX).select_related("user")
        n = 0
        for assoc in qs:
            if assoc.associate_id in PROTECTED:
                continue
            if not _is_dummy(assoc):
                continue
            changed = False
            if assoc.status != Associate.Status.INACTIVE:
                assoc.status = Associate.Status.INACTIVE
                changed = True
            if changed:
                assoc.save(update_fields=["status", "updated_at"])
            n += 1
            self.stdout.write(f"  inactive {assoc.associate_id}")
        self.stdout.write(self.style.SUCCESS(f"Inactivated {n} dummy ID(s) ({PREFIX}*). Not deleted."))

    @transaction.atomic
    def _create(self, sponsor_id: str) -> None:
        sponsor = Associate.objects.filter(associate_id__iexact=sponsor_id, is_deleted=False).first()
        if not sponsor:
            raise SystemExit(f"Sponsor {sponsor_id} not found")

        existing = list(
            Associate.objects.filter(associate_id__startswith=PREFIX).values_list("associate_id", flat=True)
        )
        if existing:
            self.stdout.write(f"Already present: {', '.join(sorted(existing))}")
            self.stdout.write("Skip create. Use --inactivate to mark them inactive.")
            return

        made: dict[str, Associate] = {}

        def add(aid: str, parent: Associate, idx: int) -> Associate:
            assoc = self._make(aid, parent=parent, idx=idx)
            made[aid] = assoc
            return assoc

        # Same 25-shape as the smoke tree, sponsor is the live head (not a dummy).
        u01 = add(f"{PREFIX}U01", sponsor, 1)
        u02 = add(f"{PREFIX}U02", sponsor, 2)
        u03 = add(f"{PREFIX}U03", sponsor, 3)
        add(f"{PREFIX}U04", sponsor, 4)
        add(f"{PREFIX}U05", sponsor, 5)

        chain_parent = u01
        for i in range(6, 16):
            chain_parent = add(f"{PREFIX}U{i:02d}", chain_parent, i)

        for i in range(16, 19):
            add(f"{PREFIX}U{i:02d}", u02, i)
        for i in range(19, 26):
            add(f"{PREFIX}U{i:02d}", u03, i)

        self.stdout.write(self.style.SUCCESS(f"Created {len(made)} dummy IDs under {sponsor.associate_id}"))
        for aid in dummy_ids():
            a = made[aid]
            parent = a.sponsor.associate_id if a.sponsor_id else "—"
            self.stdout.write(f"  {aid}  sponsor={parent}  status={a.status}")
        self.stdout.write(f"Login password for all dummy IDs: {PASSWORD}")
        self.stdout.write("No investment / no commission credited. Say delete to --inactivate.")

    def _make(self, aid: str, *, parent: Associate, idx: int) -> Associate:
        email = f"{aid.lower()}@joyclub.dummy"
        mobile = f"8815{idx:06d}"[:10]
        user = User.objects.create_user(
            username=aid,
            email=email,
            password=PASSWORD,
            first_name="Dummy",
            last_name=f"15-{idx:02d}",
        )
        assoc = Associate.objects.create(
            user=user,
            associate_id=aid,
            referral_code=generate_referral_code(),
            mobile=mobile,
            sponsor=parent,
            sponsor_associate_id=parent.associate_id,
            lead_reference=parent.associate_id,
            status=Associate.Status.INACTIVE,
            join_amount=0,
            personal_business=0,
            total_business=0,
            city="Jaipur",
            state="Rajasthan",
            country="India",
        )
        assoc.set_login_password(PASSWORD)
        assoc.save(update_fields=["login_password", "updated_at"])
        if not GenealogyNode.objects.filter(associate=parent).exists():
            if parent.sponsor_id:
                GenealogyService.attach_under_sponsor(parent, parent.sponsor, force=True)
            else:
                GenealogyService.ensure_root(parent)
        if GenealogyNode.objects.filter(associate=assoc).exists():
            return assoc
        GenealogyService.attach_under_sponsor(assoc, parent, force=True)
        WalletService.ensure_wallets(assoc)
        return assoc
