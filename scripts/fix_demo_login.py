"""Diagnose + fix demo associate login on VPS/local."""
from django.contrib.auth import authenticate, get_user_model
from associates.models import Associate
from wallets.services import WalletService

User = get_user_model()
AID = "JOY99999999"
PWD = "demo1234"

u = User.objects.filter(username__iexact=AID).first()
print("USER", bool(u), getattr(u, "email", None), getattr(u, "user_type", None), getattr(u, "is_active", None))
if u:
    print("PWD_OK", u.check_password(PWD))
    print("HAS_ASSOC", hasattr(u, "associate"), getattr(getattr(u, "associate", None), "associate_id", None), getattr(getattr(u, "associate", None), "status", None))

a = Associate.objects.filter(associate_id__iexact=AID).first()
print("ASSOC", bool(a), getattr(a, "user_id", None), getattr(a, "mobile", None), getattr(a, "status", None))

# Recreate/fix
from decimal import Decimal
from genealogy.services import GenealogyService

sponsor = Associate.objects.filter(associate_id="JOY00000001").first() or Associate.objects.filter(sponsor__isnull=True).first()
print("SPONSOR", getattr(sponsor, "associate_id", None))

if not sponsor:
    raise SystemExit("NO_SPONSOR")

email = "demo.associate@joyclub.member"
if u:
    u.set_password(PWD)
    u.username = AID
    u.email = email
    u.user_type = "associate"
    u.is_active = True
    u.is_staff = False
    u.save()
else:
    u = User.objects.create_user(
        email=email,
        password=PWD,
        username=AID,
        first_name="Demo",
        last_name="Associate",
        phone="9999999999",
        user_type="associate",
    )

if a:
    a.user = u
    a.associate_id = AID
    a.mobile = "9999999999"
    a.sponsor = sponsor
    a.sponsor_associate_id = sponsor.associate_id
    a.lead_reference = sponsor.associate_id
    a.status = Associate.Status.ACTIVE
    a.kyc_verified = True
    a.save()
else:
    a = Associate.objects.create(
        user=u,
        associate_id=AID,
        sponsor=sponsor,
        sponsor_associate_id=sponsor.associate_id,
        lead_reference=sponsor.associate_id,
        mobile="9999999999",
        status=Associate.Status.ACTIVE,
        kyc_verified=True,
        join_amount=Decimal("0"),
    )

WalletService.ensure_wallets(a)
try:
    GenealogyService.attach_under_sponsor(a, sponsor)
except Exception as e:
    print("GEN", type(e).__name__, e)

auth = authenticate(username=u.email, password=PWD) or authenticate(username=AID, password=PWD)
print("AUTH_RESULT", bool(auth), getattr(auth, "username", None))
print("CHECK", u.check_password(PWD), u.username, u.email)
print("READY", AID, PWD)
