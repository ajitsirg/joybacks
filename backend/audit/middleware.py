"""Lightweight request context for audit IP capture."""

from __future__ import annotations

import threading

_local = threading.local()


def get_request_ip() -> str | None:
    return getattr(_local, "ip", None)


def get_user_agent() -> str:
    return getattr(_local, "ua", "")


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        real_ip = request.META.get("HTTP_X_REAL_IP")
        if xff:
            _local.ip = xff.split(",")[0].strip()
        elif real_ip:
            _local.ip = real_ip.strip()
        else:
            _local.ip = request.META.get("REMOTE_ADDR")
        _local.ua = request.META.get("HTTP_USER_AGENT", "")
        try:
            return self.get_response(request)
        finally:
            _local.ip = None
            _local.ua = ""
