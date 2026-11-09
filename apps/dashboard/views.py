"""
Tableau de bord administrateur sur mesure (distinct de l'admin native /admin/).

Accès réservé aux comptes actifs membres du staff (is_staff) ou superutilisateurs :
- visiteur anonyme  -> redirection vers la page de connexion ;
- compte non staff  -> erreur 403.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from apps.bookings.models import Reservation
from apps.circuits.models import Circuit
from apps.guides.models import Guide
from apps.locations.models import Destination
from apps.reviews.models import Avis
from apps.tourism.models import SiteTouristique

MOIS_COURTS_FR = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]
NB_MOIS_GRAPHIQUE = 12
NB_CIRCUITS_TOP = 5


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Autorise uniquement les comptes actifs du staff ou les superutilisateurs."""

    def test_func(self):
        user = self.request.user
        return user.is_active and (user.is_staff or user.is_superuser)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def premiers_jours_des_derniers_mois(nb_mois, reference):
    """Liste chronologique des 1ers jours des `nb_mois` derniers mois (mois courant inclus)."""
    annee, mois = reference.year, reference.month
    resultat = []
    for _ in range(nb_mois):
        resultat.append(date(annee, mois, 1))
        mois -= 1
        if mois == 0:
            mois, annee = 12, annee - 1
    return list(reversed(resultat))


def verifier_disponibilite_guide(reservation):
    """
    Retourne un message d'erreur si le guide de la réservation ne peut pas être
    engagé sur ses dates, sinon None.
    Contrôles : profil vérifié et actif, aucune période d'indisponibilité,
    aucune autre réservation déjà acceptée qui chevauche la période.
    """
    guide = reservation.guide
    if guide is None:
        return None

    debut = reservation.date_depart
    fin = reservation.date_fin or reservation.date_depart
    periode = f"du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}"

    if not guide.est_disponible_sur_periode(debut, fin):
        return (
            f"Le guide {guide} n'est pas disponible {periode} "
            "(profil non vérifié ou inactif, ou période d'indisponibilité déclarée)."
        )

    conflit = (
        Reservation.objects.filter(
            guide=guide,
            statut=Reservation.Statut.ACCEPTEE,
            date_depart__lte=fin,
            date_fin__gte=debut,
        )
        .exclude(pk=reservation.pk)
        .first()
    )
    if conflit:
        return f"Le guide {guide} est déjà engagé {periode} sur la réservation {conflit.reference}."
    return None


def redirection_securisee(request, url_par_defaut):
    """Redirige vers `next` uniquement s'il pointe vers ce site (protection open redirect)."""
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(url_par_defaut)


# ---------------------------------------------------------------------------
# Vues
# ---------------------------------------------------------------------------
class DashboardAdminView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aujourd_hui = timezone.localdate()
        debut_mois = aujourd_hui.replace(day=1)
        statuts_confirmes = [Reservation.Statut.ACCEPTEE, Reservation.Statut.TERMINEE]
        User = get_user_model()

        # --- Indicateurs clés (une requête agrégée par table) ---
        context["stats_reservations"] = Reservation.objects.aggregate(
            total=Count("id"),
            en_attente=Count("id", filter=Q(statut=Reservation.Statut.EN_ATTENTE)),
            acceptees=Count("id", filter=Q(statut=Reservation.Statut.ACCEPTEE)),
            refusees=Count("id", filter=Q(statut=Reservation.Statut.REFUSEE)),
            annulees=Count("id", filter=Q(statut=Reservation.Statut.ANNULEE)),
            terminees=Count("id", filter=Q(statut=Reservation.Statut.TERMINEE)),
            ce_mois=Count("id", filter=Q(created_at__date__gte=debut_mois)),
            chiffre_affaires=Sum("montant_total", filter=Q(statut__in=statuts_confirmes)),
            voyageurs_confirmes=Sum("nombre_personnes", filter=Q(statut__in=statuts_confirmes)),
        )
        context["stats_visiteurs"] = User.objects.aggregate(
            total=Count("id", filter=Q(role=User.Role.TOURISTE)),
            nouveaux_ce_mois=Count(
                "id",
                filter=Q(role=User.Role.TOURISTE, date_joined__date__gte=debut_mois),
            ),
        )
        context["stats_catalogue"] = {
            "circuits_actifs": Circuit.objects.actifs().count(),
            "circuits_total": Circuit.objects.count(),
            "guides_verifies": Guide.objects.verifies().count(),
            "guides_en_attente": Guide.objects.filter(
                statut_verification=Guide.StatutVerification.EN_ATTENTE
            ).count(),
            "sites_actifs": SiteTouristique.objects.actifs().count(),
            "destinations_actives": Destination.objects.actifs().count(),
            "avis_a_moderer": Avis.objects.filter(
                statut_validation=Avis.StatutValidation.EN_ATTENTE
            ).count(),
        }

        # --- Graphique 1 : réservations mensuelles (12 derniers mois, par date de demande) ---
        mois = premiers_jours_des_derniers_mois(NB_MOIS_GRAPHIQUE, aujourd_hui)
        lignes = (
            Reservation.objects.filter(created_at__date__gte=mois[0])
            .annotate(mois=TruncMonth("created_at"))
            .values("mois")
            .annotate(
                total=Count("id"),
                confirmees=Count("id", filter=Q(statut__in=statuts_confirmes)),
            )
        )
        par_mois = {}
        for ligne in lignes:
            cle = ligne["mois"]
            cle = date(cle.year, cle.month, 1)
            par_mois[cle] = ligne
        context["chart_mensuel"] = {
            "labels": [f"{MOIS_COURTS_FR[m.month - 1]} {m:%y}" for m in mois],
            "total": [par_mois.get(m, {}).get("total", 0) for m in mois],
            "confirmees": [par_mois.get(m, {}).get("confirmees", 0) for m in mois],
        }

        # --- Graphique 2 : circuits les plus demandés (toutes demandes confondues) ---
        top_circuits = list(
            Circuit.objects.annotate(
                nb_demandes=Count("reservations"),
                nb_voyageurs=Sum("reservations__nombre_personnes"),
            )
            .filter(nb_demandes__gt=0)
            .order_by("-nb_demandes", "titre")[:NB_CIRCUITS_TOP]
        )
        context["chart_circuits"] = {
            "labels": [c.titre for c in top_circuits],
            "demandes": [c.nb_demandes for c in top_circuits],
            "voyageurs": [c.nb_voyageurs or 0 for c in top_circuits],
        }

        # --- Réservations en attente (départs les plus proches en premier) ---
        reservations_en_attente = list(
            Reservation.objects.filter(statut=Reservation.Statut.EN_ATTENTE)
            .select_related("circuit", "guide", "utilisateur")
            .order_by("date_depart", "created_at")[:10]
        )
        for reservation in reservations_en_attente:
            reservation.alerte_guide = verifier_disponibilite_guide(reservation)
            reservation.depart_passe = reservation.date_depart < aujourd_hui
        context["reservations_en_attente"] = reservations_en_attente

        context["reservations_recentes"] = (
            Reservation.objects.select_related("circuit", "guide")
            .exclude(statut=Reservation.Statut.EN_ATTENTE)
            .order_by("-updated_at")[:8]
        )
        context["aujourd_hui"] = aujourd_hui
        return context


class ReservationStatutUpdateView(StaffRequiredMixin, View):
    """
    Accepte ou refuse une réservation « En attente » depuis le dashboard.
    POST uniquement (protégé par le middleware CSRF de Django).
    """

    http_method_names = ["post"]
    ACTIONS = {
        "accepter": Reservation.Statut.ACCEPTEE,
        "refuser": Reservation.Statut.REFUSEE,
    }

    def post(self, request, reference):
        url_dashboard = reverse("dashboard:index")
        action = request.POST.get("action", "")
        nouveau_statut = self.ACTIONS.get(action)
        if nouveau_statut is None:
            messages.error(request, "Action non reconnue.")
            return redirection_securisee(request, url_dashboard)

        with transaction.atomic():
            reservation = get_object_or_404(
                Reservation.objects.select_for_update(of=("self",)),
                reference=reference,
            )

            if reservation.statut != Reservation.Statut.EN_ATTENTE:
                messages.warning(
                    request,
                    f"La réservation {reservation.reference} a déjà été traitée "
                    f"(statut actuel : {reservation.get_statut_display()}).",
                )
                return redirection_securisee(request, url_dashboard)

            if nouveau_statut == Reservation.Statut.ACCEPTEE:
                alerte = verifier_disponibilite_guide(reservation)
                if alerte:
                    messages.error(request, f"Impossible d'accepter {reservation.reference} : {alerte}")
                    return redirection_securisee(request, url_dashboard)

            reservation.statut = nouveau_statut
            reservation.date_reponse = timezone.now()
            champs = ["statut", "date_reponse", "updated_at"]
            if nouveau_statut == Reservation.Statut.REFUSEE:
                reservation.motif_refus_ou_annulation = request.POST.get("motif", "").strip()[:1000]
                champs.append("motif_refus_ou_annulation")
            reservation.save(update_fields=champs)

        if nouveau_statut == Reservation.Statut.ACCEPTEE:
            messages.success(request, f"Réservation {reservation.reference} acceptée.")
        else:
            messages.info(request, f"Réservation {reservation.reference} refusée.")
        return redirection_securisee(request, url_dashboard)

