from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.circuits.models import Circuit
from apps.guides.models import Guide

from .forms import ReservationForm
from .models import Reservation


class ReservationCreateView(CreateView):
    """
    Étape 1 & 2 du tunnel de réservation :
    - Saisie et vérification des informations (circuit, dates, nombre de voyageurs, coordonnées)
    - Enregistrement en base avec référence unique et tarif figé
    - Redirection vers la page de confirmation
    """

    model = Reservation
    form_class = ReservationForm
    template_name = "bookings/reservation_form.html"

    def _get_initial_circuit(self):
        slug = self.kwargs.get("circuit_slug") or self.request.GET.get("circuit")
        if slug:
            return get_object_or_404(
                Circuit.objects.actifs().select_related("destination_depart__region__pays", "guide_referent"),
                slug=slug,
            )
        return None

    def _get_initial_guide(self):
        slug = self.request.GET.get("guide")
        if slug:
            return get_object_or_404(Guide.objects.verifies(), slug=slug)
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["initial_circuit"] = self._get_initial_circuit()
        kwargs["initial_guide"] = self._get_initial_guide()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial_circuit = self._get_initial_circuit()
        context["circuit_selectionne"] = initial_circuit
        context["circuits_catalogue"] = (
            Circuit.objects.actifs()
            .select_related("destination_depart__region__pays", "guide_referent")
            .order_by("-en_vedette", "titre")
        )
        return context

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.utilisateur = self.request.user
        response = super().form_valid(form)
        self.request.session["derniere_reservation_ref"] = self.object.reference
        messages.success(
            self.request,
            f"Votre demande de réservation {self.object.reference} a bien été enregistrée !",
        )
        return response

    def get_success_url(self):
        return reverse("bookings:confirmation", kwargs={"reference": self.object.reference})


class ReservationConfirmationView(DetailView):
    """
    Étape 3 du tunnel : page de confirmation avec récapitulatif complet et numéro de référence.
    Accessible au propriétaire de la réservation, à l'administrateur, ou au visiteur
    venant tout juste de soumettre sa réservation (via sa session).
    """

    model = Reservation
    template_name = "bookings/reservation_confirmation.html"
    context_object_name = "reservation"
    slug_field = "reference"
    slug_url_kwarg = "reference"

    def get_queryset(self):
        return Reservation.objects.select_related(
            "circuit__destination_depart__region__pays",
            "guide",
            "pays_visiteur",
            "utilisateur",
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        ref_session = self.request.session.get("derniere_reservation_ref")
        est_proprietaire = user.is_authenticated and (obj.utilisateur_id == user.pk or user.is_staff)
        if not (est_proprietaire or ref_session == obj.reference):
            raise Http404("Réservation introuvable ou accès non autorisé.")
        return obj


class ReservationListView(LoginRequiredMixin, ListView):
    """Liste dédiée des réservations de l'utilisateur connecté."""

    model = Reservation
    template_name = "bookings/reservation_list.html"
    context_object_name = "reservations"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            Reservation.objects.filter(utilisateur=self.request.user)
            .select_related("circuit__destination_depart__region__pays", "guide")
            .order_by("-created_at")
        )
        statut = self.request.GET.get("statut", "").strip()
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statut_filtre"] = self.request.GET.get("statut", "").strip()
        context["statuts_choices"] = Reservation.Statut.choices
        return context


class ReservationCancelView(LoginRequiredMixin, View):
    """Annulation par le visiteur d'une réservation encore en attente (POST sécurisé par CSRF)."""

    def post(self, request, reference):
        reservation = get_object_or_404(
            Reservation,
            reference=reference,
            utilisateur=request.user,
        )
        if reservation.statut != Reservation.Statut.EN_ATTENTE:
            messages.warning(
                request,
                "Seules les réservations « En attente » peuvent être annulées directement en ligne.",
            )
        else:
            reservation.statut = Reservation.Statut.ANNULEE
            reservation.motif_refus_ou_annulation = "Annulée par le visiteur depuis son espace personnel."
            reservation.date_reponse = timezone.now()
            reservation.save(update_fields=["statut", "motif_refus_ou_annulation", "date_reponse", "updated_at"])
            messages.info(request, f"La réservation {reservation.reference} a été annulée.")

        next_url = request.POST.get("next") or reverse("accounts:dashboard")
        return redirect(next_url)
