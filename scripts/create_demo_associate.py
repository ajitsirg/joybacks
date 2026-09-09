"""Create / reset a single demo associate for app demos.

Usage (inside API container or local backend):
  python manage.py shell < scripts/create_demo_associate.py
  # or:
  python /app/scripts/...  (prefer manage.py shell -c via deploy helper)
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model

from associates.models import Associate
from genealogy.services import GenealogyService
from wallets.services import WalletService

User = get_user_model()

ASSOCIATE_ID = "JOY99999999"
MOBILE = "9999999999"
PASSWORD = "demo1234"
EMAIL = "demo.associate@joyclub.member"
FIRST = "Demo"
LAST = "Associate"


def main() -> None:
    sponsor = (
        Associate.objects.filter(associate_id="JOY00000001").first()
        or Associate.objects.filter(sponsor__isnull=True).order_by("created_at").first()
    )
    if not sponsor:
        raise SystemExit("No root/sponsor associate found. Run seed_joyclub first.")

    user = User.objects.filter(username=ASSOCIATE_ID).first()
    if not user:
        user = User.objects.filter(email=EMAIL).first()
    if user:
        user.username = ASSOCIATE_ID
        user.email = EMAIL
        user.first_name = FIRST
        user.last_name = LAST
        user.phone = MOBILE
        user.user_type = "associate"
        user.is_active = True
        user.set_password(PASSWORD)
        user.save()
        created_user = False
    else:
        user = User.objects.create_user(
            email=EMAIL,
            password=PASSWORD,
            username=ASSOCIATE_ID,
            first_name=FIRST,
            last_name=LAST,
            phone=MOBILE,
            user_type="associate",
        )
        created_user = True

    assoc = Associate.objects.filter(associate_id=ASSOCIATE_ID).first()
    if not assoc:
        assoc = Associate.objects.filter(user=user).first()
    if assoc:
        assoc.user = user
        assoc.associate_id = ASSOCIATE_ID
        assoc.mobile = MOBILE
        assoc.sponsor = sponsor
        assoc.sponsor_associate_id = sponsor.associate_id
        assoc.lead_reference = sponsor.associate_id
        assoc.status = Associate.Status.ACTIVE
        assoc.kyc_verified = True
        assoc.card_tier = Associate.CardTier.GRAY
        assoc.flag_color = "gray"
        assoc.join_amount = Decimal("0")
        assoc.save()
        created_assoc = False
    else:
        assoc = Associate.objects.create(
            user=user,
            associate_id=ASSOCIATE_ID,
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id,
            lead_reference=sponsor.associate_id,
            mobile=MOBILE,
            status=Associate.Status.ACTIVE,
            kyc_verified=True,
            card_tier=Associate.CardTier.GRAY,
            flag_color="gray",
            join_amount=Decimal("0"),
        )
        created_assoc = True

    WalletService.ensure_wallets(assoc)
    try:
        GenealogyService.attach_under_sponsor(assoc, sponsor)
    except Exception as exc:  # already attached / leg full — non-fatal for demo
        print(f"GENEALOGY_NOTE {type(exc).__name__}: {exc}")

    print(
        "OK",
        "user_created" if created_user else "user_updated",
        "assoc_created" if created_assoc else "assoc_updated",
        ASSOCIATE_ID,
        PASSWORD,
        f"sponsor={sponsor.associate_id}",
    )


main()
