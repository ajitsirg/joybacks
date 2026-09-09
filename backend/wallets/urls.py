from django.urls import path

from wallets.views import (
    FundTransferPackagesView,
    FundTransferRequestApproveView,
    FundTransferRequestListCreateView,
    FundTransferRequestRejectView,
    FundTransferView,
    LedgerListView,
    WalletListView,
)

urlpatterns = [
    path("", WalletListView.as_view(), name="wallets"),
    path("ledger/", LedgerListView.as_view(), name="ledger"),
    path("transfer/packages/", FundTransferPackagesView.as_view(), name="fund-transfer-packages"),
    path(
        "transfer/requests/",
        FundTransferRequestListCreateView.as_view(),
        name="fund-transfer-requests",
    ),
    path(
        "transfer/requests/<uuid:pk>/approve/",
        FundTransferRequestApproveView.as_view(),
        name="fund-transfer-request-approve",
    ),
    path(
        "transfer/requests/<uuid:pk>/reject/",
        FundTransferRequestRejectView.as_view(),
        name="fund-transfer-request-reject",
    ),
    path("transfer/", FundTransferView.as_view(), name="fund-transfer"),
]
