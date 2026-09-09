from decimal import Decimal

from associates.models import Associate
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import has_finance_permission
from wallets.fund_packages import FUND_TRANSFER_AMOUNTS, PAYMENT_METHODS, format_lakh
from wallets.models import FundTransferRequest, LedgerEntry, Wallet
from wallets.serializers import FundTransferRequestSerializer, LedgerEntrySerializer, WalletSerializer
from wallets.visibility import exclude_buyer_self_roi
from wallets.services import WalletService
from wallets.transfer import (
    admin_fund_transfer,
    approve_fund_transfer_request,
    create_fund_transfer_request,
    reject_fund_transfer_request,
)


def _visible_associate_ids(user):
    """None = all (staff). Empty list = none. Else self + downline IDs."""
    if user.is_staff or user.is_superuser:
        return None
    me = getattr(user, "associate", None)
    if not me:
        return []
    from genealogy.models import GenealogyClosure

    return list(GenealogyClosure.objects.filter(ancestor=me).values_list("descendant_id", flat=True))


class WalletListView(generics.ListAPIView):
    serializer_class = WalletSerializer
    filterset_fields = ["wallet_type", "associate__associate_id"]

    def get_queryset(self):
        qs = Wallet.objects.select_related("associate")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        me = getattr(user, "associate", None)
        if not me:
            return qs.none()
        # Default: own wallets only. Filter by associate_id to view downline member.
        target = (self.request.query_params.get("associate__associate_id") or "").strip()
        if target:
            ids = _visible_associate_ids(user) or []
            return qs.filter(associate_id__in=ids, associate__associate_id__iexact=target)
        return qs.filter(associate=me)


class LedgerListView(generics.ListAPIView):
    serializer_class = LedgerEntrySerializer
    filterset_fields = ["entry_type", "wallet__wallet_type", "wallet__associate__associate_id"]
    search_fields = ["reference", "narration"]

    def get_queryset(self):
        qs = LedgerEntry.objects.select_related("wallet", "wallet__associate")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            scoped = qs
        else:
            me = getattr(user, "associate", None)
            if not me:
                return qs.none()
            target = (self.request.query_params.get("wallet__associate__associate_id") or "").strip()
            if target:
                ids = _visible_associate_ids(user) or []
                scoped = qs.filter(
                    wallet__associate_id__in=ids,
                    wallet__associate__associate_id__iexact=target,
                )
            else:
                scoped = qs.filter(wallet__associate=me)

        roi_level_only = self.request.query_params.get("roi_level_only")
        roi_base_only = self.request.query_params.get("roi_base_only")
        include_buyer_roi = self.request.query_params.get("include_buyer_roi")
        if roi_level_only in ("1", "true", "yes") or self.request.query_params.get("roi_on_roi") in (
            "1",
            "true",
            "yes",
        ):
            scoped = scoped.filter(
                Q(reference__regex=r"-L\d+$")
                | Q(narration__regex=r"(Growth|ROI) L\d+")
                | Q(narration__icontains="ROI-on-ROI")
            )
        elif roi_base_only in ("1", "true", "yes"):
            scoped = scoped.filter(
                Q(reference__regex=r"MRI-.*-M\d+$") | Q(narration__regex=r"^ROI M\d+")
            ).exclude(reference__regex=r"-L\d+$")
        elif include_buyer_roi not in ("1", "true", "yes"):
            # Investor's own ₹2,200 is never shown (calculation base only).
            scoped = exclude_buyer_self_roi(scoped)
        return scoped


class FundTransferPackagesView(APIView):
    """Fixed package amounts + under-leg recipients for fund transfer UI."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        packages = [
            {
                "amount": str(a),
                "label": format_lakh(a),
                "amount_number": float(a),
            }
            for a in FUND_TRANSFER_AMOUNTS
        ]
        me = getattr(request.user, "associate", None)
        main_balance = None
        personal_balance = None
        personal_business = None
        recipients: list[dict] = []

        if me:
            WalletService.ensure_wallets(me)
            main_w = Wallet.objects.filter(associate=me, wallet_type=Wallet.WalletType.MAIN).first()
            personal_w = Wallet.objects.filter(associate=me, wallet_type=Wallet.WalletType.PERSONAL).first()
            main_balance = str(main_w.balance) if main_w else "0.00"
            personal_balance = str(personal_w.balance) if personal_w else "0.00"
            personal_business = str(me.personal_business or 0)

            from genealogy.models import GenealogyClosure

            # Under-leg only — members cannot send funds to themselves
            from django.db.models import Q

            leg_ids = list(
                GenealogyClosure.objects.filter(ancestor=me, depth__gt=0).values_list(
                    "descendant_id", flat=True
                )
            )
            under_qs = (
                Associate.objects.filter(is_deleted=False)
                .filter(Q(id__in=leg_ids) | Q(sponsor=me))
                .exclude(pk=me.pk)
                .select_related("user")
                .order_by("associate_id")
                .distinct()
            )
            for assoc in under_qs:
                recipients.append(
                    {
                        "associate_id": assoc.associate_id,
                        "name": assoc.user.get_full_name()
                        or assoc.user.username
                        or assoc.associate_id,
                        "is_self": False,
                        "status": assoc.status,
                    }
                )

        return Response(
            {
                "packages": packages,
                "payment_methods": [
                    {"code": code, "label": label} for code, label in PAYMENT_METHODS
                ],
                "recipients": recipients,
                "can_fund_transfer": bool(
                    request.user.is_staff or request.user.is_superuser
                ),
                "can_request_fund_transfer": bool(
                    me and not (request.user.is_staff or request.user.is_superuser)
                ),
                "associate_id": me.associate_id if me else None,
                "main_balance": main_balance,
                "personal_balance": personal_balance,
                "personal_business": personal_business,
                "min_package": str(FUND_TRANSFER_AMOUNTS[0]),
            }
        )


class FundTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        is_staff = has_finance_permission(user, "wallets.transfer", "fund.transfer")
        associate_id = (request.data.get("associate_id") or "").strip()
        amount_raw = request.data.get("amount", "0")
        narration = request.data.get("narration", "")
        payment_method = (request.data.get("payment_method") or "").strip()
        apply_business = str(request.data.get("apply_business", "")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        if not is_staff:
            return Response(
                {
                    "detail": (
                        "Only admin can transfer funds. Submit a fund transfer request instead."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            wallet_type = request.data.get("wallet_type", Wallet.WalletType.MAIN)
            entry = admin_fund_transfer(
                actor=user,
                to_associate_id=associate_id,
                wallet_type=wallet_type,
                amount=Decimal(str(amount_raw)),
                narration=narration or "Admin fund transfer",
                apply_business=apply_business,
                payment_method=payment_method,
                from_associate_id=(request.data.get("from_associate_id") or "").strip(),
                company_mint=str(request.data.get("company_mint", "")).lower()
                in ("1", "true", "yes", "on"),
            )
            return Response(LedgerEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Associate.DoesNotExist:
            return Response({"detail": "Associate not found"}, status=400)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)


def _fund_request_qs():
    return FundTransferRequest.objects.select_related(
        "requester",
        "requester__user",
        "beneficiary",
        "beneficiary__user",
        "reviewed_by",
    )


class FundTransferRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = FundTransferRequestSerializer
    filterset_fields = ["status"]
    search_fields = [
        "requester__associate_id",
        "beneficiary__associate_id",
        "note",
        "utr",
    ]

    def get_queryset(self):
        qs = _fund_request_qs()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        me = getattr(user, "associate", None)
        if not me:
            return qs.none()
        return qs.filter(requester=me)

    def create(self, request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return Response(
                {"detail": "Admin transfers funds directly from Fund Transfer."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            obj = create_fund_transfer_request(
                actor=request.user,
                to_associate_id=(request.data.get("associate_id") or "").strip(),
                amount=Decimal(str(request.data.get("amount", "0"))),
                payment_method=(request.data.get("payment_method") or "").strip(),
                note=request.data.get("note") or request.data.get("narration") or "",
                utr=request.data.get("utr") or request.data.get("transaction_id") or "",
                proof=request.FILES.get("proof") or request.FILES.get("document"),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Associate.DoesNotExist:
            return Response({"detail": "Associate not found"}, status=400)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            FundTransferRequestSerializer(obj, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class FundTransferRequestApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not has_finance_permission(request.user, "fund.transfer", "wallets.transfer"):
            return Response(
                {"detail": "Finance fund-transfer permission is required"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            obj = _fund_request_qs().get(pk=pk)
        except FundTransferRequest.DoesNotExist:
            return Response({"detail": "Request not found"}, status=404)
        apply_raw = request.data.get("apply_business")
        apply_business = None
        if apply_raw is not None:
            apply_business = str(apply_raw).lower() in ("1", "true", "yes", "on")
        try:
            obj = approve_fund_transfer_request(
                request_obj=obj,
                actor=request.user,
                apply_business=apply_business,
                password=request.data.get("password") or request.data.get("confirm_password") or "",
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(FundTransferRequestSerializer(obj, context={"request": request}).data)


class FundTransferRequestRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not has_finance_permission(request.user, "fund.transfer", "wallets.transfer"):
            return Response(
                {"detail": "Finance fund-transfer permission is required"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            obj = _fund_request_qs().get(pk=pk)
        except FundTransferRequest.DoesNotExist:
            return Response({"detail": "Request not found"}, status=404)
        try:
            obj = reject_fund_transfer_request(
                request_obj=obj,
                actor=request.user,
                reason=request.data.get("reason") or "",
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(FundTransferRequestSerializer(obj).data)
