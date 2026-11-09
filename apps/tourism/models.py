"""
Catalogue touristique : catégories, sites touristiques et leur galerie.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import (
    ActiveQuerySet,
    BasePhoto,
    GeoPointModel,
    SluggedModel,
    TimeStampedModel,
)
from apps.core.utils import UploadToPath
from apps.locations.models import Destination


class CategorieSite(TimeStampedModel, SluggedModel):
    """
    Catégorie gérée depuis l'admin (ex. « Mosquée en terre », « Parc national »),
    rattachée à une grande famille (historique, naturel…) pour le filtrage.
    """

    class Famille(models.TextChoices):
        HISTORIQUE = "historique", "Historique & patrimoine"
        NATUREL = "naturel", "Naturel & paysages"
        CULTUREL = "culturel", "Culturel & traditions"
        RELIGIEUX = "religieux", "Religieux & spirituel"

    nom = models.CharField("nom", max_length=100, unique=True)
    famille = models.CharField("famille", max_length=20, choices=Famille.choices)
    description = models.TextField("description", blank=True)
    icone = models.CharField(
        "icône",
        max_length=50,
        blank=True,
        help_text="Classe Bootstrap Icons, ex : bi-bank, bi-tree, bi-sun",
    )
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)

    class Meta:
        verbose_name = "catégorie de site"
        verbose_name_plural = "catégories de sites"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class SiteTouristique(TimeStampedModel, SluggedModel, GeoPointModel):
    destination = models.ForeignKey(
        Destination,
        verbose_name="destination",
        on_delete=models.PROTECT,
        related_name="sites",
    )
    categorie = models.ForeignKey(
        CategorieSite,
        verbose_name="catégorie",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sites",
    )
    nom = models.CharField("nom", max_length=150)
    description_courte = models.CharField(
        "accroche",
        max_length=255,
        help_text="Une ou deux phrases affichées sur les cartes de la liste.",
    )
    description = models.TextField("description")
    histoire = models.TextField(
        "histoire",
        blank=True,
        help_text="Origines, contexte historique, légendes, anecdotes.",
    )
    adresse = models.CharField("adresse / accès", max_length=255, blank=True)
    horaires_ouverture = models.TextField(
        "horaires d'ouverture",
        blank=True,
        help_text="Ex : Tous les jours de 8h à 18h — fermé le vendredi de 12h à 15h.",
    )
    prix_entree = models.DecimalField(
        "prix d'entrée (FCFA)",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="0 si l'entrée est gratuite.",
    )
    duree_visite_minutes = models.PositiveSmallIntegerField(
        "durée de visite conseillée (minutes)",
        null=True,
        blank=True,
    )
    patrimoine_unesco = models.BooleanField("inscrit au patrimoine mondial de l'UNESCO", default=False)
    image_principale = models.ImageField(
        "image principale",
        upload_to=UploadToPath("tourism/sites"),
    )
    en_vedette = models.BooleanField("mis en avant sur l'accueil", default=False)
    est_actif = models.BooleanField("publié", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "site touristique"
        verbose_name_plural = "sites touristiques"
        ordering = ["nom"]
        indexes = [
            models.Index(fields=["est_actif", "en_vedette"], name="site_publication_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(prix_entree__gte=0),
                name="site_prix_entree_positif",
            ),
        ]

    def __str__(self):
        return self.nom

    @property
    def pays(self):
        return self.destination.region.pays

    @property
    def est_gratuit(self):
        return self.prix_entree == 0


class PhotoSite(BasePhoto):
    site = models.ForeignKey(
        SiteTouristique,
        verbose_name="site touristique",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(
        "image",
        upload_to=UploadToPath("tourism/sites/galerie", slug_attr="site.slug"),
    )

    class Meta(BasePhoto.Meta):
        verbose_name = "photo du site"
        verbose_name_plural = "photos du site"
