"""Absolute media URLs with cache-busting query so UI refreshes after replace."""

from __future__ import annotations

from typing import Any


def absolute_media_url(file_field, request=None, *, version: Any = None) -> str | None:
    if not file_field:
        return None
    try:
        url = file_field.url
    except ValueError:
        return None
    if request is not None:
        url = request.build_absolute_uri(url)
    if version is not None:
        stamp = version
        if hasattr(version, "timestamp"):
            try:
                stamp = int(version.timestamp())
            except (OSError, OverflowError, ValueError, TypeError):
                stamp = str(version)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}v={stamp}"
    return url
