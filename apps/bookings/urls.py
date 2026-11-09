from django.urls import path

from .views import (
    ReservationCancelView,
    ReservationConfirmationView,
    ReservationCreateView,
    ReservationListView,
)

app_name = "bookings"

urlpatterns = [
    path("", ReservationListView.as_view(), name="list"),
    path("nouvelle/", ReservationCreateView.as_view(), name="create"),
    path("nouvelle/<slug:circuit_slug>/", ReservationCreateView.as_view(), name="create_for_circuit"),
    path("confirmation/<str:reference>/", ReservationConfirmationView.as_view(), name="confirmation"),
    path("<str:reference>/annuler/", ReservationCancelView.as_view(), name="cancel"),
]

