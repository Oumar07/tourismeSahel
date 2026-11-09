from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.bookings.models import Reservation
from apps.circuits.models import Circuit
from apps.guides.models import Guide
from apps.locations.models import Destination
from apps.tourism.models import SiteTouristique

from .forms import AvisForm
from .models import Avis, Favori

CIBLES_AVIS = {
    "site": (SiteTouristique, "site"),
    "circuit": (Circuit, "circuit"),
    "guide": (Guide, "guide"),
}

CIBLES_FAVORIS = {
    "destination": (Destination, "destination"),
    "site": (SiteTouristique, "site"),
    "circuit": (Circuit, "circuit"),
    "guide": (Guide, "guide"),
}


def _default_return_url(cible_type, obj):
    if cible_type == "destination":
        return reverse("locations:destination_detail", kwargs={"slug": obj.slug})
    if cible_type == "site":
        return reverse("tourism:site_detail", kwargs={"slug": obj.slug})
    if cible_type == "circuit":
        return reverse("circuits:circuit_detail", kwargs={"slug": obj.slug})
    if cible_type == "guide":
        return reverse("guides:guide_detail", kwargs={"slug": obj.slug})
    return reverse("accounts:dashboard")


class SoumettreAvisView(LoginRequiredMixin, View):
    """
    Réception en POST (sécurisée par CSRF) d'un avis sur un site, un circuit ou un guide.
    Rattache automatiquement une réservation existante du visiteur pour activer
    le badge « Voyageur vérifié ».
    """

    def post(self, request, cible_type, slug):
        if cible_type not in CIBLES_AVIS:
            raise Http404("Type de cible invalide pour un avis.")

        model_cls, field_name = CIBLES_AVIS[cible_type]
        cible_obj = get_object_or_404(model_cls, slug=slug, est_actif=True)
        redirect_url = request.POST.get("next") or _default_return_url(cible_type, cible_obj)

        # Vérifie l'absence de doublon avant l'insertion
        if Avis.objects.filter(auteur=request.user, **{field_name: cible_obj}).exists():
            messages.warning(request, "Vous avez déjà déposé un avis pour cet élément.")
            return redirect(redirect_url)

        # Pré-instancie l'avis avec son auteur et sa cible pour que ModelForm.is_valid()
        # exécute Avis.clean() et les contraintes SQL avec la cible déjà renseignée.
        avis_instance = Avis(auteur=request.user, **{field_name: cible_obj})
        form = AvisForm(request.POST, instance=avis_instance)
        if form.is_valid():
            avis = form.save(commit=False)

            # Recherche d'une réservation confirmée/terminée correspondante (« Voyageur vérifié »)
            reservations_qs = Reservation.objects.filter(
                utilisateur=request.user,
                statut__in=[Reservation.Statut.ACCEPTEE, Reservation.Statut.TERMINEE],
            )
            if field_name == "circuit":
                reservations_qs = reservations_qs.filter(circuit=cible_obj)
            elif field_name == "guide":
                reservations_qs = reservations_qs.filter(guide=cible_obj)
            elif field_name == "site":
                reservations_qs = reservations_qs.filter(circuit__sites=cible_obj)

            avis.reservation = reservations_qs.order_by("-date_depart").first()
            avis.save()
            messages.success(
                request,
                "Merci pour votre témoignage ! Votre avis a été enregistré et sera publié après validation.",
            )
        else:
            for field_errors in form.errors.values():
                for err in field_errors:
                    messages.error(request, err)

        return redirect(redirect_url)


class ToggleFavoriView(LoginRequiredMixin, View):
    """Ajout ou retrait d'un favori en POST (sécurisé par CSRF)."""

    def post(self, request, cible_type, slug):
        if cible_type not in CIBLES_FAVORIS:
            raise Http404("Type de cible invalide pour un favori.")

        model_cls, field_name = CIBLES_FAVORIS[cible_type]
        cible_obj = get_object_or_404(model_cls, slug=slug, est_actif=True)
        redirect_url = request.POST.get("next") or _default_return_url(cible_type, cible_obj)

        favori_qs = Favori.objects.filter(utilisateur=request.user, **{field_name: cible_obj})
        if favori_qs.exists():
            favori_qs.delete()
            messages.info(request, f"« {cible_obj} » a été retiré de vos favoris.")
        else:
            Favori.objects.create(utilisateur=request.user, **{field_name: cible_obj})
            messages.success(request, f"« {cible_obj} » a été ajouté à vos favoris.")

        return redirect(redirect_url)


class FavoriListView(LoginRequiredMixin, ListView):
    """Page dédiée aux favoris du visiteur connecté."""

    model = Favori
    template_name = "reviews/favorite_list.html"
    context_object_name = "favoris"
    paginate_by = 12

    def get_queryset(self):
        return (
            Favori.objects.filter(utilisateur=self.request.user)
            .select_related(
                "destination__region__pays",
                "site__destination__region__pays",
                "circuit__destination_depart__region__pays",
                "guide",
            )
            .order_by("-created_at")
        )
