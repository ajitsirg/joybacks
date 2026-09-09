from rest_framework import serializers

from associates.models import Associate


class GenealogyNodeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    username = serializers.CharField(source="associate_id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    sponsor_id = serializers.CharField(source="sponsor_associate_id", read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Associate
        fields = (
            "id",
            "associate_id",
            "username",
            "referral_code",
            "name",
            "email",
            "mobile",
            "status",
            "card_tier",
            "flag_color",
            "join_amount",
            "lead_reference",
            "sponsor_id",
            "total_business",
            "personal_business",
            "earning_level",
            "earning_level_name",
            "performance_level",
            "performance_level_name",
            "direct_count",
            "direct_active_count",
            "children_count",
            "kyc_verified",
        )

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_children_count(self, obj):
        node = getattr(obj, "genealogy_node", None)
        return node.children.count() if node else 0
