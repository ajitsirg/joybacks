"""Admin purge: archive associate into recycle bin + clear live points."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from associates.models import Associate, DeletedAssociate
from associates.purge import PurgeError, archive_associate, restore_associate
from genealogy.models import GenealogyClosure
from genealogy.services import GenealogyService
from wallets.models import LedgerEntry, Wallet
from wallets.services import WalletService

User = get_user_model()


class AssociatePurgeTests(TestCase):
    def _assoc(self, code: str, *, sponsor: Associate | None = None) -> Associate:
        user = User.objects.create_user(
            username=code.lower(),
            email=f"{code.lower()}@purge.test",
            password="x",
            user_type=User.UserType.ASSOCIATE,
        )
        a = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}"[:20],
            mobile=("9" + "".join(ch for ch in code if ch.isdigit()) * 4)[:10],
            sponsor=sponsor,
            sponsor_associate_id=sponsor.associate_id if sponsor else "",
            status=Associate.Status.ACTIVE,
            personal_business=Decimal("220000.00"),
            total_business=Decimal("220000.00"),
            join_amount=Decimal("220000.00"),
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        WalletService.ensure_wallets(a)
        WalletService.credit(
            associate=a,
            wallet_type=Wallet.WalletType.ROI,
            amount=Decimal("2200.00"),
            reference=f"T-{code}",
            narration="test points",
        )
        return a

    def test_archive_hides_from_live_keeps_in_bucket(self):
        root = self._assoc("JOYPURGEROOT")
        child = self._assoc("JOYPURGECH01", sponsor=root)
        uid = child.user_id
        wid = Wallet.objects.get(associate=child, wallet_type=Wallet.WalletType.ROI).pk

        result = archive_associate(associate=child)

        self.assertTrue(result["archived"])
        self.assertFalse(Associate.objects.filter(associate_id="JOYPURGECH01").exists())
        archived = Associate.all_objects.get(associate_id="JOYPURGECH01")
        self.assertTrue(archived.is_deleted)
        self.assertTrue(DeletedAssociate.all_objects.filter(pk=archived.pk).exists())
        self.assertFalse(User.objects.get(pk=uid).is_active)
        self.assertTrue(Wallet.all_objects.filter(pk=wid, is_deleted=True).exists())
        self.assertFalse(Wallet.objects.filter(pk=wid).exists())

        root.refresh_from_db()
        self.assertEqual(root.direct_count, 0)

    def test_mid_delete_shifts_underleg_to_upper_level(self):
        upper = self._assoc("JOYPURGEUP01")
        mid = self._assoc("JOYPURGEMID01", sponsor=upper)
        child = self._assoc("JOYPURGECH02", sponsor=mid)
        grand = self._assoc("JOYPURGEGR01", sponsor=child)

        result = archive_associate(associate=mid)

        self.assertEqual(result["reparent_to"], upper.associate_id)
        child.refresh_from_db()
        grand.refresh_from_db()
        self.assertEqual(child.sponsor_id, upper.pk)
        self.assertEqual(grand.sponsor_id, child.pk)
        self.assertTrue(Associate.all_objects.get(pk=mid.pk).is_deleted)
        self.assertTrue(
            GenealogyClosure.objects.filter(ancestor=upper, descendant=child, depth=1).exists()
        )
        self.assertTrue(
            GenealogyClosure.objects.filter(ancestor=upper, descendant=grand, depth=2).exists()
        )

    def test_restore_from_bucket(self):
        root = self._assoc("JOYPURGER03")
        child = self._assoc("JOYPURGECH03", sponsor=root)
        archive_associate(associate=child)
        restore_associate(associate=Associate.all_objects.get(associate_id="JOYPURGECH03"))
        alive = Associate.objects.get(associate_id="JOYPURGECH03")
        self.assertFalse(alive.is_deleted)
        self.assertTrue(alive.user.is_active)

    def test_hard_destroy(self):
        root = self._assoc("JOYPURGER04")
        child = self._assoc("JOYPURGECH04", sponsor=root)
        uid = child.user_id
        archive_associate(associate=child, hard=True)
        self.assertFalse(Associate.all_objects.filter(associate_id="JOYPURGECH04").exists())
        self.assertFalse(User.objects.filter(pk=uid).exists())

    def test_cannot_purge_protected_root_id(self):
        user = User.objects.create_user(
            username="siddhi",
            email="siddhi@purge.test",
            password="x",
            user_type=User.UserType.ASSOCIATE,
        )
        a = Associate.objects.create(
            user=user,
            associate_id="JOYSIDDHI01",
            referral_code="RSIDDHI01",
            mobile="9000000001",
            status=Associate.Status.ACTIVE,
        )
        GenealogyService.ensure_root(a)
        with self.assertRaises(PurgeError):
            archive_associate(associate=a)
