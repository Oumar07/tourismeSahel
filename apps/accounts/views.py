from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView

from .forms import ConnexionForm, InscriptionForm, ProfilForm


class InscriptionView(CreateView):
    """Création d'un compte visiteur et connexion automatique."""

    form_class = InscriptionForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f"Bienvenue sur TourismeSahel, {self.object.first_name or self.object.username} ! Votre compte a été créé.",
        )
        return response


class ConnexionView(LoginView):
    """Connexion d'un visiteur, d'un guide ou d'un administrateur."""

    form_class = ConnexionForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "Vous êtes maintenant connecté.")
        return super().form_valid(form)


class DeconnexionView(LogoutView):
    """Déconnexion sécurisée (requiert une requête POST avec jeton CSRF)."""

    next_page = reverse_lazy("core:home")

    def post(self, request, *args, **kwargs):
        messages.info(request, "Vous avez été déconnecté. À très bientôt au Sahel !")
        return super().post(request, *args, **kwargs)


class DashboardVisiteurView(LoginRequiredMixin, View):
    """
    Espace personnel du visiteur :
    - Vue d'ensemble de ses réservations et de leurs statuts
    - Liste de ses favoris (destinations, sites, circuits, guides)
    - Historique de ses avis et de leur statut de validation
    - Modification de ses informations personnelles (POST sécurisé par CSRF)
    """

    template_name = "accounts/dashboard.html"

    def _build_context(self, request, profil_form=None):
        user = request.user
        reservations = (
            user.reservations.select_related("circuit__destination_depart__region__pays", "guide")
            .order_by("-created_at")
        )
        favoris = (
            user.favoris.select_related("destination__region__pays", "site__destination", "circuit", "guide")
            .order_by("-created_at")
        )
        avis_list = (
            user.avis.select_related("site", "circuit", "guide")
            .order_by("-created_at")
        )

        aujourd_hui = timezone.localdate()
        stats = {
            "nb_reservations": reservations.count(),
            "nb_a_venir": reservations.filter(date_depart__gte=aujourd_hui).exclude(statut__in=["refusee", "annulee"]).count(),
            "nb_favoris": favoris.count(),
            "nb_avis": avis_list.count(),
        }

        return {
            "reservations": reservations,
            "favoris": favoris,
            "avis_list": avis_list,
            "stats": stats,
            "profil_form": profil_form or ProfilForm(instance=user),
            "active_tab": request.GET.get("tab", "reservations"),
        }

    def get(self, request):
        return render(request, self.template_name, self._build_context(request))

    def post(self, request):
        profil_form = ProfilForm(request.POST, request.FILES, instance=request.user)
        if profil_form.is_valid():
            profil_form.save()
            messages.success(request, "Votre profil a été mis à jour avec succès.")
            return redirect("accounts:dashboard")

        context = self._build_context(request, profil_form=profil_form)
        context["active_tab"] = "profil"
        messages.error(request, "Veuillez corriger les erreurs signalées dans le formulaire.")
        return render(request, self.template_name, context)
