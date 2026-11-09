from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("administration/", include("apps.dashboard.urls", namespace="dashboard")),
    path("", include("apps.core.urls", namespace="core")),
    path("comptes/", include("apps.accounts.urls", namespace="accounts")),
    path("destinations/", include("apps.locations.urls", namespace="locations")),
    path("sites/", include("apps.tourism.urls", namespace="tourism")),
    path("circuits/", include("apps.circuits.urls", namespace="circuits")),
    path("guides/", include("apps.guides.urls", namespace="guides")),
    path("reservations/", include("apps.bookings.urls", namespace="bookings")),
    path("", include("apps.reviews.urls", namespace="reviews")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
