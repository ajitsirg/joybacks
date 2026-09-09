from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from associates.models import Associate
from genealogy.services import GenealogyService

User = get_user_model()


class AssociateProfileAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _assoc(self, code: str, *, sponsor: Associate | None = None) -> Associate:
        user = User.objects.create_user(
            username=code.lower(), password="x", email=f"{code.lower()}@t.test"
        )
        digits = "".join(ch for ch in code if ch.isdigit()) or "1"
        a = Associate.objects.create(
            user=user,
            associate_id=code,
            referral_code=f"R{code}"[:20],
            mobile=(digits * 4)[:10],
            sponsor=sponsor,
            status=Associate.Status.ACTIVE,
        )
        if sponsor is None:
            GenealogyService.ensure_root(a)
        else:
            GenealogyService.attach_under_sponsor(a, sponsor, force=True)
        return a

    def test_sponsor_can_open_downline_profile(self):
        root = self._assoc("JOYTREE01")
        child = self._assoc("JOYTREE02", sponsor=root)
        self.client.force_authenticate(user=root.user)
        resp = self.client.get(f"/api/v1/associates/{child.associate_id}/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["associate_id"], child.associate_id)

    def test_unrelated_associate_cannot_open_profile(self):
        a = self._assoc("JOYTREEA1")
        b = self._assoc("JOYTREEB1")
        self.client.force_authenticate(user=a.user)
        resp = self.client.get(f"/api/v1/associates/{b.associate_id}/")
        self.assertEqual(resp.status_code, 404)
