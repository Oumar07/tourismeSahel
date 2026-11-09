from django.urls import path

from .views import FavoriListView, SoumettreAvisView, ToggleFavoriView

app_name = "reviews"

urlpatterns = [
    path("favoris/", FavoriListView.as_view(), name="favorite_list"),
    path("favoris/basculer/<str:cible_type>/<slug:slug>/", ToggleFavoriView.as_view(), name="toggle_favorite"),
    path("avis/ajouter/<str:cible_type>/<slug:slug>/", SoumettreAvisView.as_view(), name="add_review"),
]

