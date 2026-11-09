from django.urls import path

from .views import SiteTouristiqueDetailView, SiteTouristiqueListView

app_name = "tourism"

urlpatterns = [
    path("", SiteTouristiqueListView.as_view(), name="site_list"),
    path("<slug:slug>/", SiteTouristiqueDetailView.as_view(), name="site_detail"),
]

