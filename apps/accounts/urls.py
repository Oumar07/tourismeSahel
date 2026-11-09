from django.urls import path

from .views import (
    ConnexionView,
    DashboardVisiteurView,
    DeconnexionView,
    InscriptionView,
)

app_name = "accounts"

urlpatterns = [
    path("inscription/", InscriptionView.as_view(), name="register"),
    path("connexion/", ConnexionView.as_view(), name="login"),
    path("deconnexion/", DeconnexionView.as_view(), name="logout"),
    path("tableau-de-bord/", DashboardVisiteurView.as_view(), name="dashboard"),
    path("profil/", DashboardVisiteurView.as_view(), name="profile"),
]

