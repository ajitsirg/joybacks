from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model

from audit.models import AuditLog

User = get_user_model()


def write_audit(
    *,
    actor: User | None,
    action: str,
    module: str,
    object_type: str = "",
    object_id: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        module=module,
        object_type=object_type,
        object_id=object_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
    )
