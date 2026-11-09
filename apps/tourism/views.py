from django.db.models import Avg, Count, Q
from django.views.generic import DetailView, ListView

from apps.circuits.models import Circuit
from apps.locations.models import Destination, Pays
from apps.reviews.forms import AvisForm
from apps.reviews.models import Avis, Favori

from .models import CategorieSite, SiteTouristique


class SiteTouristiqueListView(ListView):
    """Catalogue des sites touristiques avec filtres multicritères."""

    model = SiteTouristique
    template_name = "tourism/site_list.html"
    context_object_name = "sites"
    paginate_by = 9

    def get_queryset(self):
        filtre_avis_valide = Q(avis__statut_validation=Avis.StatutValidation.VALIDE)
        queryset = (
            SiteTouristique.objects.actifs()
            .select_related("destination__region__pays", "categorie")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide),
            )
        )

        q = self.request.GET.get("q", "").strip()
        pays_slug = self.request.GET.get("pays", "").strip()
        destination_slug = self.request.GET.get("destination", "").strip()
        categorie_slug = self.request.GET.get("categorie", "").strip()
        famille = self.request.GET.get("famille", "").strip()
        unesco = self.request.GET.get("unesco", "").strip()
        gratuit = self.request.GET.get("gratuit", "").strip()
        tri = self.request.GET.get("tri", "").strip()

        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q)
                | Q(description_courte__icontains=q)
                | Q(description__icontains=q)
                | Q(histoire__icontains=q)
                | Q(destination__nom__icontains=q)
                | Q(destination__region__pays__nom__icontains=q)
            )
        if pays_slug:
            queryset = queryset.filter(
                Q(destination__region__pays__slug=pays_slug)
                | Q(destination__region__pays__code_iso__iexact=pays_slug)
            )
        if destination_slug:
            queryset = queryset.filter(destination__slug=destination_slug)
        if categorie_slug:
            queryset = queryset.filter(categorie__slug=categorie_slug)
        if famille:
            queryset = queryset.filter(categorie__famille=famille)
        if unesco == "1":
            queryset = queryset.filter(patrimoine_unesco=True)
        if gratuit == "1":
            queryset = queryset.filter(prix_entree=0)

        if tri == "note":
            queryset = queryset.order_by("-note_moyenne", "-nb_avis", "nom")
        elif tri == "prix_asc":
            queryset = queryset.order_by("prix_entree", "nom")
        elif tri == "prix_desc":
            queryset = queryset.order_by("-prix_entree", "nom")
        else:
            queryset = queryset.order_by("-en_vedette", "-patrimoine_unesco", "nom")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pays_slug = self.request.GET.get("pays", "").strip()

        context["pays_list"] = Pays.objects.actifs().order_by("nom")
        destinations_qs = Destination.objects.actifs().select_related("region__pays").order_by("nom")
        if pays_slug:
            destinations_qs = destinations_qs.filter(
                Q(region__pays__slug=pays_slug) | Q(region__pays__code_iso__iexact=pays_slug)
            )
        context["destinations_list"] = destinations_qs
        context["categories_list"] = CategorieSite.objects.order_by("ordre", "nom")
        context["familles_choices"] = CategorieSite.Famille.choices

        context["filtres"] = {
            "q": self.request.GET.get("q", "").strip(),
            "pays": pays_slug,
            "destination": self.request.GET.get("destination", "").strip(),
            "categorie": self.request.GET.get("categorie", "").strip(),
            "famille": self.request.GET.get("famille", "").strip(),
            "unesco": self.request.GET.get("unesco", "").strip(),
            "gratuit": self.request.GET.get("gratuit", "").strip(),
            "tri": self.request.GET.get("tri", "").strip(),
        }
        return context


class SiteTouristiqueDetailView(DetailView):
    """Fiche détaillée d'un site touristique : histoire, horaires, galerie, circuits et avis."""

    model = SiteTouristique
    template_name = "tourism/site_detail.html"
    context_object_name = "site"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            SiteTouristique.objects.actifs()
            .select_related("destination__region__pays", "categorie")
            .prefetch_related("photos")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = self.object

        avis_qs = site.avis.valides().select_related("auteur").order_by("-created_at")
        context["avis_list"] = avis_qs
        context["stats_avis"] = avis_qs.aggregate(
            moyenne=Avg("note"),
            total=Count("id"),
        )

        context["circuits_associes"] = (
            Circuit.objects.actifs()
            .filter(sites=site)
            .select_related("destination_depart__region__pays", "guide_referent")
            .distinct()[:3]
        )

        context["sites_proches"] = (
            SiteTouristique.objects.actifs()
            .filter(destination=site.destination)
            .exclude(pk=site.pk)
            .select_related("categorie", "destination__region__pays")[:3]
        )
        context["avis_form"] = AvisForm()
        user = self.request.user
        if user.is_authenticated:
            context["est_en_favori"] = Favori.objects.filter(utilisateur=user, site=site).exists()
            context["deja_note"] = Avis.objects.filter(auteur=user, site=site).exists()
        else:
            context["est_en_favori"] = False
            context["deja_note"] = False
        return context
