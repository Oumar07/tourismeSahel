from django.urls import path

from .views import CircuitDetailView, CircuitListView

app_name = "circuits"

urlpatterns = [
    path("", CircuitListView.as_view(), name="circuit_list"),
    path("<slug:slug>/", CircuitDetailView.as_view(), name="circuit_detail"),
]

