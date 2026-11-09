from django.urls import path

from .views import DashboardAdminView, ReservationStatutUpdateView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardAdminView.as_view(), name="index"),
    path(
        "reservations/<str:reference>/statut/",
        ReservationStatutUpdateView.as_view(),
        name="reservation_statut",
    ),
]

