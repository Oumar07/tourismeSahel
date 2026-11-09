from django import forms
from django.contrib import messages
from django.core.validators import validate_email
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.accounts.forms import BootstrapFormMixin
from apps.circuits.models import Circuit
from apps.guides.models import Guide
from apps.locations.models import Destination, Pays
from apps.reviews.models import Avis
from apps.tourism.models import CategorieSite, SiteTouristique


class ContactForm(BootstrapFormMixin, forms.Form):
    """Formulaire de contact public sécurisé par CSRF."""

    SUJETS = [
        ("information", "Demande d'informations sur un voyage"),
        ("sur_mesure", "Devis pour un circuit sur mesure"),
        ("reservation", "Question sur une réservation existante"),
        ("partenariat", "Partenariat / Devenir guide certifié"),
        ("autre", "Autre demande"),
    ]

    nom_complet = forms.CharField(label="Nom complet", max_length=120)
    email = forms.EmailField(label="Adresse e-mail")
    telephone = forms.CharField(label="Téléphone / WhatsApp (optionnel)", max_length=30, required=False)
    sujet = forms.ChoiceField(label="Objet de votre message", choices=SUJETS)
    message = forms.CharField(
        label="Votre message",
        min_length=15,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Précisez vos dates envisagées, le pays souhaité ou toute question utile…",
            }
        ),
    )


class HomeView(TemplateView):
    """
    Page d'accueil de TourismeSahel :
    - Barre de recherche rapide (pays, catégorie, mot-clé)
    - Destinations populaires
    - Sites touristiques emblématiques
    - Circuits phares & guides certifiés
    - Avis récents vérifiés des voyageurs
    """

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtre_avis_valide = Q(avis__statut_validation=Avis.StatutValidation.VALIDE)

        context["pays_list"] = Pays.objects.actifs().order_by("nom")
        context["categories_list"] = CategorieSite.objects.order_by("ordre", "nom")

        context["destinations_populaires"] = (
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
            .order_by("-en_vedette", "-nb_sites", "nom")[:6]
        )

        context["sites_vedettes"] = (
            SiteTouristique.objects.actifs()
            .select_related("destination__region__pays", "categorie")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide),
            )
            .order_by("-en_vedette", "-patrimoine_unesco", "nom")[:4]
        )

        context["circuits_vedettes"] = (
            Circuit.objects.actifs()
            .select_related("destination_depart__region__pays", "guide_referent")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide),
            )
            .order_by("-en_vedette", "tarif_par_personne")[:3]
        )

        context["guides_vedettes"] = (
            Guide.objects.verifies()
            .prefetch_related("langues", "specialites", "regions__pays")
            .annotate(
                note_moyenne=Avg("avis__note", filter=filtre_avis_valide),
                nb_avis=Count("avis", filter=filtre_avis_valide),
            )
            .order_by("-en_vedette", "-annees_experience")[:4]
        )

        context["avis_recents"] = (
            Avis.objects.valides()
            .select_related("auteur", "site", "circuit", "guide")
            .order_by("-created_at")[:6]
        )

        context["stats"] = {
            "nb_pays": Pays.objects.actifs().count(),
            "nb_destinations": Destination.objects.actifs().count(),
            "nb_sites": SiteTouristique.objects.actifs().count(),
            "nb_circuits": Circuit.objects.actifs().count(),
            "nb_guides": Guide.objects.verifies().count(),
        }
        return context


class AboutView(TemplateView):
    """Page « À propos » présentant la mission et les engagements de TourismeSahel."""

    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {
            "nb_pays": Pays.objects.actifs().count(),
            "nb_destinations": Destination.objects.actifs().count(),
            "nb_sites": SiteTouristique.objects.actifs().count(),
            "nb_circuits": Circuit.objects.actifs().count(),
            "nb_guides": Guide.objects.verifies().count(),
        }
        return context


class ContactView(FormView):
    """Page de contact avec formulaire interactif et coordonnées des antennes locales."""

    template_name = "core/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("core:contact")

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if user.is_authenticated:
            initial["nom_complet"] = user.get_full_name() or user.username
            initial["email"] = user.email
            initial["telephone"] = getattr(user, "telephone", "")
        sujet_get = self.request.GET.get("sujet", "")
        if sujet_get in dict(ContactForm.SUJETS):
            initial["sujet"] = sujet_get
        return initial

    def form_valid(self, form):
        nom = form.cleaned_data["nom_complet"]
        messages.success(
            self.request,
            f"Merci {nom} ! Votre message a bien été transmis à notre équipe. "
            "Nous vous répondrons sous 24 à 48 heures ouvrées.",
        )
        return super().form_valid(form)


class FaqView(TemplateView):
    """Foire aux questions sur les voyages, la sécurité, les guides et la réservation."""

    template_name = "core/faq.html"


class DevenirGuideView(TemplateView):
    """Présentation du processus de certification pour rejoindre le réseau de guides."""

    template_name = "core/devenir_guide.html"


class LegalPageView(TemplateView):
    """Pages légales (Mentions légales, Politique de confidentialité, CGV)."""

    template_name = "core/legal.html"
    page_key = "mentions"

    PAGES = {
        "mentions": {
            "badge": "Informations réglementaires",
            "titre": "Mentions légales",
            "intro": "Informations relatives à l'éditeur et à l'hébergement de la plateforme TourismeSahel.",
            "sections": [
                (
                    "Éditeur de la plateforme",
                    "TourismeSahel SAS — Réseau de promotion du tourisme culturel et durable dans l'espace sahélien. "
                    "Sièges de coordination : Dakar (Sénégal), Bamako (Mali), Niamey (Niger) et Ouagadougou (Burkina Faso). "
                    "Contact : contact@tourismesahel.com.",
                ),
                (
                    "Propriété intellectuelle",
                    "L'ensemble des contenus éditoriaux, éléments graphiques, logos et photographies publiés sur "
                    "TourismeSahel sont protégés par le droit d'auteur. Toute reproduction non autorisée est interdite.",
                ),
                (
                    "Rôle d'intermédiation",
                    "TourismeSahel met en relation les voyageurs avec des guides locaux détenteurs d'une carte "
                    "professionnelle vérifiée par notre équipe de modération.",
                ),
            ],
        },
        "confidentialite": {
            "badge": "Protection des données",
            "titre": "Politique de confidentialité",
            "intro": "Engagements de TourismeSahel concernant la collecte et la protection de vos données personnelles.",
            "sections": [
                (
                    "Données collectées",
                    "Nous collectons uniquement les informations strictement nécessaires au traitement de vos réservations "
                    "(identité, coordonnées de contact, préférences de voyage) et à la gestion de votre espace visiteur.",
                ),
                (
                    "Partage limité",
                    "Vos coordonnées ne sont transmises qu'au guide certifié en charge de votre circuit afin d'assurer "
                    "l'organisation logistique de votre séjour. Aucune donnée n'est cédée à des tiers commerciaux.",
                ),
                (
                    "Vos droits",
                    "Vous pouvez à tout moment modifier vos informations depuis votre espace visiteur ou demander la "
                    "suppression de votre compte en écrivant à contact@tourismesahel.com.",
                ),
            ],
        },
        "cgv": {
            "badge": "Conditions contractuelles",
            "titre": "Conditions Générales de Réservation (CGV)",
            "intro": "Modalités applicables aux demandes de réservation de circuits accompagnés sur TourismeSahel.",
            "sections": [
                (
                    "Processus de réservation et tarif figé",
                    "Toute demande déposée sur la plateforme génère une référence unique (TS-AAAA-XXXXXX) avec un tarif "
                    "par personne garanti au moment de la demande. La réservation devient ferme dès sa validation par "
                    "notre équipe et le guide référent.",
                ),
                (
                    "Annulation par le voyageur",
                    "Tant qu'une demande est au statut « En attente », elle peut être annulée sans frais directement "
                    "depuis l'espace visiteur.",
                ),
                (
                    "Tourisme responsable",
                    "Les participants s'engagent à respecter les coutumes locales, les sites classés et les consignes "
                    "environnementales communiquées par leur guide accompagnateur.",
                ),
            ],
        },
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page"] = self.PAGES.get(self.page_key, self.PAGES["mentions"])
        return context


class NewsletterSubscribeView(View):
    """Inscription rapide à la newsletter depuis le pied de page (POST + CSRF)."""

    http_method_names = ["post"]

    def post(self, request):
        email = request.POST.get("email", "").strip()
        try:
            validate_email(email)
        except forms.ValidationError:
            messages.error(request, "Veuillez saisir une adresse e-mail valide pour la newsletter.")
        else:
            messages.success(
                request,
                f"Merci ! L'adresse {email} est bien inscrite à la lettre d'inspiration TourismeSahel.",
            )

        referer = request.META.get("HTTP_REFERER", "")
        if referer and url_has_allowed_host_and_scheme(
            referer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(referer)
        return redirect("core:home")
