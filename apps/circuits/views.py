"""
Catalogue et fiches détaillées des circuits touristiques accompagnés.
"""
from django.db.models import Avg, Count, Q
from django.views.generic import DetailView, ListView

from apps.locations.models import Pays
from apps.reviews.forms import AvisForm
from apps.reviews.models import Avis, Favori

from .models import Circuit


class CircuitListView(ListView):
    """Liste filtrable et paginée des circuits publiés."""

    model = Circuit
    template_name = "circuits/circuit_list.html"
    context_object_name = "circuits"
    paginate_by = 9

    def get_queryset(self):
        filtre_avis_valide = Q(avis__statut_validation=Avis.StatutValidation.VALIDE)
        qs = (
            Circuit.objects.actifs()
            .select_related("destination_depart__region__pays", "guide_referent")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide, distinct=True),
                nb_etapes=Count("etapes", distinct=True),
            )
        )

        q = self.request.GET.get("q", "").strip()
        pays_slug = self.request.GET.get("pays", "").strip()
        difficulte = self.request.GET.get("difficulte", "").strip()
        tri = self.request.GET.get("tri", "").strip()

        if q:
            qs = qs.filter(
                Q(titre__icontains=q)
                | Q(description_courte__icontains=q)
                | Q(description__icontains=q)
                | Q(destination_depart__nom__icontains=q)
                | Q(destination_depart__region__pays__nom__icontains=q)
            )
        if pays_slug:
            qs = qs.filter(destination_depart__region__pays__slug=pays_slug)
        if difficulte in dict(Circuit.Difficulte.choices):
            qs = qs.filter(difficulte=difficulte)

        if tri == "prix_asc":
            qs = qs.order_by("tarif_par_personne", "titre")
        elif tri == "prix_desc":
            qs = qs.order_by("-tarif_par_personne", "titre")
        elif tri == "duree":
            qs = qs.order_by("duree_jours", "titre")
        else:
            qs = qs.order_by("-en_vedette", "tarif_par_personne", "titre")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pays_list"] = Pays.objects.actifs().order_by("nom")
        context["difficultes"] = Circuit.Difficulte.choices
        context["filtres_actuels"] = {
            "q": self.request.GET.get("q", "").strip(),
            "pays": self.request.GET.get("pays", "").strip(),
            "difficulte": self.request.GET.get("difficulte", "").strip(),
            "tri": self.request.GET.get("tri", "").strip(),
        }
        return context


class CircuitDetailView(DetailView):
    """Fiche détaillée d'un circuit : programme jour par jour, inclus/non inclus, guide, avis et réservation."""

    model = Circuit
    template_name = "circuits/circuit_detail.html"
    context_object_name = "circuit"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Circuit.objects.actifs().select_related(
            "destination_depart__region__pays",
            "guide_referent",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        circuit = self.object

        context["etapes"] = circuit.etapes.select_related("site__destination").order_by("jour", "ordre")
        context["inclus_liste"] = [ligne.strip() for ligne in circuit.inclus.splitlines() if ligne.strip()]
        context["non_inclus_liste"] = [ligne.strip() for ligne in circuit.non_inclus.splitlines() if ligne.strip()]

        avis_qs = circuit.avis.valides().select_related("auteur").order_by("-created_at")
        context["avis_list"] = avis_qs
        context["stats_avis"] = avis_qs.aggregate(
            moyenne=Avg("note"),
            total=Count("id"),
        )
        context["avis_form"] = AvisForm()

        user = self.request.user
        if user.is_authenticated:
            context["est_en_favori"] = Favori.objects.filter(utilisateur=user, circuit=circuit).exists()
            context["deja_note"] = Avis.objects.filter(auteur=user, circuit=circuit).exists()
        else:
            context["est_en_favori"] = False
            context["deja_note"] = False

        context["circuits_similaires"] = (
            Circuit.objects.actifs()
            .select_related("destination_depart__region__pays")
            .exclude(pk=circuit.pk)
            .order_by("-en_vedette", "tarif_par_personne")[:3]
        )
        return context
