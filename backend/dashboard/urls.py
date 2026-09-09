from django.urls import path

from dashboard.views import AdminDashboardView, BusinessReportView

urlpatterns = [
    path("admin/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("business-report/", BusinessReportView.as_view(), name="business-report"),
]
