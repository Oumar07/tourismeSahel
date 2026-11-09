"""
Annuaire et profils détaillés des guides touristiques locaux certifiés.
"""
from django.db.models import Avg, Count, Q
from django.views.generic import DetailView, ListView

from apps.locations.models import Pays
from apps.reviews.forms import AvisForm
from apps.reviews.models import Avis, Favori

from .models import Guide, Langue, SpecialiteGuide


class GuideListView(ListView):
    """Annuaire filtrable des guides vérifiés et actifs."""

    model = Guide
    template_name = "guides/guide_list.html"
    context_object_name = "guides"
    paginate_by = 12

    def get_queryset(self):
        filtre_avis_valide = Q(avis__statut_validation=Avis.StatutValidation.VALIDE)
        qs = (
            Guide.objects.verifies()
            .prefetch_related("langues", "specialites", "regions__pays")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide, distinct=True),
                nb_circuits=Count("circuits", filter=Q(circuits__est_actif=True), distinct=True),
            )
        )

        q = self.request.GET.get("q", "").strip()
        pays_slug = self.request.GET.get("pays", "").strip()
        langue_code = self.request.GET.get("langue", "").strip()
        specialite_slug = self.request.GET.get("specialite", "").strip()

        if q:
            qs = qs.filter(
                Q(nom_complet__icontains=q)
                | Q(titre_professionnel__icontains=q)
                | Q(bio__icontains=q)
                | Q(regions__nom__icontains=q)
            ).distinct()
        if pays_slug:
            qs = qs.filter(regions__pays__slug=pays_slug).distinct()
        if langue_code:
            qs = qs.filter(langues__code=langue_code).distinct()
        if specialite_slug:
            qs = qs.filter(specialites__slug=specialite_slug).distinct()

        return qs.order_by("-en_vedette", "-annees_experience", "nom_complet")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pays_list"] = Pays.objects.actifs().order_by("nom")
        context["langues_list"] = Langue.objects.order_by("nom")
        context["specialites_list"] = SpecialiteGuide.objects.order_by("nom")
        context["filtres_actuels"] = {
            "q": self.request.GET.get("q", "").strip(),
            "pays": self.request.GET.get("pays", "").strip(),
            "langue": self.request.GET.get("langue", "").strip(),
            "specialite": self.request.GET.get("specialite", "").strip(),
        }
        return context


class GuideDetailView(DetailView):
    """Profil public complet d'un guide certifié : bio, langues, circuits animés et avis."""

    model = Guide
    template_name = "guides/guide_detail.html"
    context_object_name = "guide"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Guide.objects.verifies().prefetch_related("langues", "specialites", "regions__pays")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guide = self.object

        context["circuits_animes"] = (
            guide.circuits.actifs()
            .select_related("destination_depart__region__pays")
            .order_by("-en_vedette", "tarif_par_personne")
        )

        avis_qs = guide.avis.valides().select_related("auteur").order_by("-created_at")
        context["avis_list"] = avis_qs
        context["stats_avis"] = avis_qs.aggregate(
            moyenne=Avg("note"),
            total=Count("id"),
        )
        context["avis_form"] = AvisForm()

        user = self.request.user
        if user.is_authenticated:
            context["est_en_favori"] = Favori.objects.filter(utilisateur=user, guide=guide).exists()
            context["deja_note"] = Avis.objects.filter(auteur=user, guide=guide).exists()
        else:
            context["est_en_favori"] = False
            context["deja_note"] = False

        return context
