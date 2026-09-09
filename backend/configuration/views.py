from rest_framework import permissions, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from configuration.models import (
    ActivationRule,
    CompanySettings,
    GenealogySettings,
    LevelIncomePlan,
    PerformanceIncomePlan,
    ROIPlan,
    RewardMaster,
    WithdrawalSettings,
)
from configuration.repository import ConfigRepository
from configuration.rewards import official_reward_payload
from configuration.serializers import (
    ActivationRuleSerializer,
    CompanySettingsSerializer,
    GenealogySettingsSerializer,
    LevelIncomePlanSerializer,
    PerformanceIncomePlanSerializer,
    ROIPlanSerializer,
    RewardMasterSerializer,
    WithdrawalSettingsSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class RuntimeConfigView(APIView):
    """Single endpoint for frontend to load all active business rules."""

    permission_classes = [AllowAny]

    def get(self, request):
        level = ConfigRepository.active_level_plan()
        perf = ConfigRepository.active_performance_plan()
        company = ConfigRepository.company()
        return Response(
            {
                "company": CompanySettingsSerializer(company, context={"request": request}).data,
                "join_packages": {
                    "show_platinum": bool(company.show_platinum_package),
                    "show_silver": bool(company.show_silver_package),
                    "show_gray": True,
                },
                "join_flow": {
                    "require_leader_approval": bool(company.require_leader_approval),
                    "require_join_otp": bool(company.require_join_otp),
                },
                "join_kyc_requirements": {
                    "pan": bool(company.require_join_pan),
                    "aadhaar": bool(company.require_join_aadhaar),
                    "bank_name": bool(company.require_join_bank_name),
                    "account_number": bool(company.require_join_account_number),
                    "ifsc": bool(company.require_join_ifsc),
                    "upi_id": bool(company.require_join_upi),
                    "profile_photo": bool(company.require_join_profile_photo),
                    "aadhaar_document": bool(company.require_join_aadhaar_document),
                    "pan_document": bool(company.require_join_pan_document),
                    "bank_document": bool(company.require_join_bank_document),
                },
                "menu": {
                    "show_income_section": bool(company.show_income_section),
                    "show_income_referral": bool(company.show_income_referral),
                    "show_income_sp_profit": bool(company.show_income_sp_profit),
                    # Same admin toggle as join_flow.require_leader_approval
                    "show_team_approvals": bool(company.require_leader_approval),
                    "show_users_flag_column": bool(company.show_users_flag_column),
                    "show_users_card_column": bool(company.show_users_card_column),
                },
                "genealogy": GenealogySettingsSerializer(ConfigRepository.genealogy()).data,
                "withdrawal": WithdrawalSettingsSerializer(ConfigRepository.withdrawal()).data,
                "level_income": LevelIncomePlanSerializer(level, context={"request": request}).data
                if level
                else None,
                "performance_income": PerformanceIncomePlanSerializer(
                    perf, context={"request": request}
                ).data
                if perf
                else None,
                "roi": ROIPlanSerializer(ConfigRepository.active_roi_plan()).data
                if ConfigRepository.active_roi_plan()
                else None,
                "rewards": official_reward_payload(),
            }
        )


class CompanySettingsViewSet(viewsets.ModelViewSet):
    queryset = CompanySettings.objects.all()
    serializer_class = CompanySettingsSerializer
    permission_classes = [IsAdminOrReadOnly]


class GenealogySettingsViewSet(viewsets.ModelViewSet):
    queryset = GenealogySettings.objects.all()
    serializer_class = GenealogySettingsSerializer
    permission_classes = [IsAdminOrReadOnly]


class WithdrawalSettingsViewSet(viewsets.ModelViewSet):
    queryset = WithdrawalSettings.objects.all()
    serializer_class = WithdrawalSettingsSerializer
    permission_classes = [IsAdminOrReadOnly]


class ActivationRuleViewSet(viewsets.ModelViewSet):
    queryset = ActivationRule.objects.all()
    serializer_class = ActivationRuleSerializer
    permission_classes = [IsAdminOrReadOnly]


class LevelIncomePlanViewSet(viewsets.ModelViewSet):
    queryset = LevelIncomePlan.objects.prefetch_related("slabs").all()
    serializer_class = LevelIncomePlanSerializer
    permission_classes = [IsAdminOrReadOnly]


class PerformanceIncomePlanViewSet(viewsets.ModelViewSet):
    queryset = PerformanceIncomePlan.objects.prefetch_related("slabs").all()
    serializer_class = PerformanceIncomePlanSerializer
    permission_classes = [IsAdminOrReadOnly]


class ROIPlanViewSet(viewsets.ModelViewSet):
    queryset = ROIPlan.objects.all()
    serializer_class = ROIPlanSerializer
    permission_classes = [IsAdminOrReadOnly]


class RewardMasterViewSet(viewsets.ModelViewSet):
    queryset = RewardMaster.objects.all()
    serializer_class = RewardMasterSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]
    filterset_fields = ["reward_type", "is_active"]
