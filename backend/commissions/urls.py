from django.urls import path

from commissions.views import AdminChargeListView, CommissionEntryListView, CommissionRunListView

urlpatterns = [
    path("runs/", CommissionRunListView.as_view(), name="commission-runs"),
    path("entries/", CommissionEntryListView.as_view(), name="commission-entries"),
    path("admin-charges/", AdminChargeListView.as_view(), name="admin-charges"),
]
