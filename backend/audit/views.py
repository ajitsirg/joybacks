from rest_framework import generics, permissions

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["module", "action", "object_type"]
    search_fields = ["action", "object_id", "actor__email"]
    ordering_fields = ["created_at"]
