"""Mobile app version check + APK download for sideload / auto-update."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def releases_dir() -> Path:
    path = Path(settings.MEDIA_ROOT) / "releases"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_version_meta() -> dict:
    version_file = releases_dir() / "version.json"
    if version_file.exists():
        try:
            data = json.loads(version_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "version_name": "1.0.0",
        "version_code": 1,
        "force": False,
        "notes": "Initial JoyClub Associate release",
    }


class AppLatestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        meta = load_version_meta()
        apk = releases_dir() / "joyclub.apk"
        return Response(
            {
                "app": "joyclub_associate",
                "version_name": str(meta.get("version_name", "1.0.0")),
                "version_code": int(meta.get("version_code", 1)),
                "force": bool(meta.get("force", False)),
                "notes": str(meta.get("notes", "")),
                "apk_available": apk.exists(),
                "download_url": request.build_absolute_uri("/api/v1/app/download/"),
            }
        )


class AppDownloadView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        apk = releases_dir() / "joyclub.apk"
        if not apk.exists():
            raise Http404("joyclub.apk is not published yet. Run mobile/scripts/publish_apk.ps1")
        return FileResponse(
            apk.open("rb"),
            as_attachment=True,
            filename="joyclub.apk",
            content_type="application/vnd.android.package-archive",
        )
