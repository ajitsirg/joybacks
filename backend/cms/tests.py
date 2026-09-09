from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from cms.models import KnowledgeItem

User = get_user_model()


class KnowledgeCenterAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="knowstaff", password="x", email="knowstaff@t.test", is_staff=True
        )
        self.member = User.objects.create_user(
            username="knowmem", password="x", email="knowmem@t.test"
        )

    def test_staff_uploads_and_associate_sees_audience(self):
        self.client.force_authenticate(user=self.staff)
        created = self.client.post(
            "/api/v1/cms/knowledge/",
            {
                "title": "How to request funds",
                "body": "Open Request Fund Transfer and add UTR.",
                "audience": "associate",
                "is_published": True,
                "media_type": "pdf",
                "file": SimpleUploadedFile("guide.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            },
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        hidden = self.client.post(
            "/api/v1/cms/knowledge/",
            {
                "title": "Finance only",
                "body": "Charge report",
                "audience": "finance",
                "is_published": True,
                "media_type": "link",
                "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            },
            format="multipart",
        )
        self.assertEqual(hidden.status_code, 201, hidden.data)

        self.assertEqual(KnowledgeItem.objects.count(), 2)
        self.client.force_authenticate(user=self.member)
        listed = self.client.get("/api/v1/cms/knowledge/")
        self.assertEqual(listed.status_code, 200, listed.data)
        rows = listed.data["results"] if isinstance(listed.data, dict) else listed.data
        titles = {r["title"] for r in rows}
        self.assertIn("How to request funds", titles)
        self.assertNotIn("Finance only", titles)

    def test_associate_cannot_upload(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.post(
            "/api/v1/cms/knowledge/",
            {"title": "Nope", "audience": "all", "media_type": "link", "video_url": "https://example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(KnowledgeItem.objects.count(), 0)
