from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.app_update import AppDownloadView, AppLatestView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/v1/app/latest/", AppLatestView.as_view(), name="app-latest"),
    path("api/v1/app/download/", AppDownloadView.as_view(), name="app-download"),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/config/", include("configuration.urls")),
    path("api/v1/associates/", include("associates.urls")),
    path("api/v1/genealogy/", include("genealogy.urls")),
    path("api/v1/wallets/", include("wallets.urls")),
    path("api/v1/commissions/", include("commissions.urls")),
    path("api/v1/audit/", include("audit.urls")),
    path("api/v1/ops/", include("operations.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/cms/", include("cms.urls")),
    path("api/v1/dashboard/", include("dashboard.urls")),
    # KYC / deposit uploads — nginx proxies /media/ here in production
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Branding is handled by Unfold UNFOLD settings (config/unfold_settings.py)
admin.site.site_header = "JoyClub Associate"
admin.site.site_title = "JoyClub Associate"
admin.site.index_title = "Control Center"
