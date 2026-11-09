from django.db.models import Avg, Count, Q
from django.views.generic import DetailView, ListView

from apps.guides.models import Guide
from apps.reviews.models import Avis, Favori

from .models import Destination, Pays, Region


class DestinationListView(ListView):
    """Catalogue des destinations avec filtres par pays, région et recherche."""

    model = Destination
    template_name = "locations/destination_list.html"
    context_object_name = "destinations"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            Destination.objects.actifs()
            .select_related("region__pays")
            .annotate(
                nb_sites=Count("sites", filter=Q(sites__est_actif=True), distinct=True),
                nb_circuits=Count(
                    "circuits_au_depart",
                    filter=Q(circuits_au_depart__est_actif=True),
                    distinct=True,
                ),
            )
        )

        q = self.request.GET.get("q", "").strip()
        pays_slug = self.request.GET.get("pays", "").strip()
        region_slug = self.request.GET.get("region", "").strip()
        en_vedette = self.request.GET.get("vedette", "").strip()
        tri = self.request.GET.get("tri", "").strip()

        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q)
                | Q(description_courte__icontains=q)
                | Q(description__icontains=q)
                | Q(region__nom__icontains=q)
                | Q(region__pays__nom__icontains=q)
            )
        if pays_slug:
            queryset = queryset.filter(
                Q(region__pays__slug=pays_slug) | Q(region__pays__code_iso__iexact=pays_slug)
            )
        if region_slug:
            queryset = queryset.filter(region__slug=region_slug)
        if en_vedette == "1":
            queryset = queryset.filter(en_vedette=True)

        if tri == "populaire":
            queryset = queryset.order_by("-nb_sites", "-en_vedette", "nom")
        elif tri == "recent":
            queryset = queryset.order_by("-created_at")
        else:
            queryset = queryset.order_by("-en_vedette", "nom")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pays_slug = self.request.GET.get("pays", "").strip()

        context["pays_list"] = Pays.objects.actifs().order_by("nom")
        regions_qs = Region.objects.actifs().select_related("pays").order_by("pays__nom", "nom")
        if pays_slug:
            regions_qs = regions_qs.filter(Q(pays__slug=pays_slug) | Q(pays__code_iso__iexact=pays_slug))
        context["regions_list"] = regions_qs

        context["filtres"] = {
            "q": self.request.GET.get("q", "").strip(),
            "pays": pays_slug,
            "region": self.request.GET.get("region", "").strip(),
            "vedette": self.request.GET.get("vedette", "").strip(),
            "tri": self.request.GET.get("tri", "").strip(),
        }
        return context


class DestinationDetailView(DetailView):
    """Fiche complète d'une destination : galerie, sites, circuits au départ et guides locaux."""

    model = Destination
    template_name = "locations/destination_detail.html"
    context_object_name = "destination"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Destination.objects.actifs()
            .select_related("region__pays")
            .prefetch_related("photos")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        destination = self.object
        filtre_avis_valide = Q(avis__statut_validation=Avis.StatutValidation.VALIDE)

        context["sites"] = (
            destination.sites.actifs()
            .select_related("categorie", "destination__region__pays")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide),
            )
            .order_by("-en_vedette", "-patrimoine_unesco", "nom")
        )

        context["circuits"] = (
            destination.circuits_au_depart.actifs()
            .select_related("guide_referent", "destination_depart__region__pays")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide),
            )
            .order_by("-en_vedette", "tarif_par_personne")
        )

        context["guides_locaux"] = (
            Guide.objects.verifies()
            .filter(regions=destination.region)
            .prefetch_related("langues", "specialites")
            .distinct()[:4]
        )

        context["autres_destinations"] = (
            Destination.objects.actifs()
            .select_related("region__pays")
            .exclude(pk=destination.pk)
            .order_by("-en_vedette", "nom")[:3]
        )
        user = self.request.user
        context["est_en_favori"] = (
            Favori.objects.filter(utilisateur=user, destination=destination).exists()
            if user.is_authenticated
            else False
        )
        return context
