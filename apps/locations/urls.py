from django.urls import path

from .views import DestinationDetailView, DestinationListView

app_name = "locations"

urlpatterns = [
    path("", DestinationListView.as_view(), name="destination_list"),
    path("<slug:slug>/", DestinationDetailView.as_view(), name="destination_detail"),
]

