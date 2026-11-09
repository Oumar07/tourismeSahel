"""
Référentiel géographique : Pays → Région → Destination (+ galerie).

Règle de suppression : PROTECT sur toute la hiérarchie. On ne peut pas
supprimer un pays qui contient encore des régions, ni une région qui
contient des destinations : on évite ainsi d'effacer par erreur tout
un pan du catalogue. Pour masquer un élément, on décoche `est_actif`.
"""
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import (
    ActiveQuerySet,
    BasePhoto,
    GeoPointModel,
    SluggedModel,
    TimeStampedModel,
)
from apps.core.utils import UploadToPath


class Pays(TimeStampedModel, SluggedModel):
    nom = models.CharField("nom", max_length=100, unique=True)
    code_iso = models.CharField(
        "code ISO",
        max_length=2,
        unique=True,
        validators=[RegexValidator(r"^[A-Z]{2}$", "Deux lettres majuscules (ISO 3166-1 alpha-2).")],
        help_text="Ex : SN, ML, NE, BF, MR, TD",
    )
    capitale = models.CharField("capitale", max_length=100, blank=True)
    devise = models.CharField("devise", max_length=50, blank=True, help_text="Ex : Franc CFA (XOF)")
    langues_officielles = models.CharField("langues officielles", max_length=150, blank=True)
    description = models.TextField("description", blank=True)
    drapeau = models.ImageField(
        "drapeau",
        upload_to=UploadToPath("locations/pays/drapeaux"),
        blank=True,
    )
    image_couverture = models.ImageField(
        "image de couverture",
        upload_to=UploadToPath("locations/pays/couvertures"),
        blank=True,
    )
    est_actif = models.BooleanField("publié", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "pays"
        verbose_name_plural = "pays"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Region(TimeStampedModel, SluggedModel):
    pays = models.ForeignKey(
        Pays,
        verbose_name="pays",
        on_delete=models.PROTECT,
        related_name="regions",
    )
    nom = models.CharField("nom", max_length=100)
    chef_lieu = models.CharField("chef-lieu", max_length=100, blank=True)
    description = models.TextField("description", blank=True)
    image = models.ImageField(
        "image",
        upload_to=UploadToPath("locations/regions"),
        blank=True,
    )
    est_actif = models.BooleanField("publiée", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "région"
        verbose_name_plural = "régions"
        ordering = ["pays__nom", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["pays", "nom"], name="unique_region_par_pays"),
        ]

    def __str__(self):
        return f"{self.nom} ({self.pays})"


class Destination(TimeStampedModel, SluggedModel, GeoPointModel):
    region = models.ForeignKey(
        Region,
        verbose_name="région",
        on_delete=models.PROTECT,
        related_name="destinations",
    )
    nom = models.CharField("nom", max_length=150)
    description_courte = models.CharField(
        "accroche",
        max_length=255,
        help_text="Une ou deux phrases affichées sur les cartes de la liste.",
    )
    description = models.TextField("description détaillée")
    image_principale = models.ImageField(
        "image principale",
        upload_to=UploadToPath("locations/destinations"),
    )
    meilleure_periode = models.CharField(
        "meilleure période de visite",
        max_length=100,
        blank=True,
        help_text="Ex : Novembre à février",
    )
    en_vedette = models.BooleanField("mise en avant sur l'accueil", default=False)
    est_actif = models.BooleanField("publiée", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "destination"
        verbose_name_plural = "destinations"
        ordering = ["nom"]
        indexes = [
            models.Index(fields=["est_actif", "en_vedette"], name="destination_publication_idx"),
        ]

    def __str__(self):
        return self.nom

    @property
    def pays(self):
        return self.region.pays


class PhotoDestination(BasePhoto):
    destination = models.ForeignKey(
        Destination,
        verbose_name="destination",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(
        "image",
        upload_to=UploadToPath("locations/destinations/galerie", slug_attr="destination.slug"),
    )

    class Meta(BasePhoto.Meta):
        verbose_name = "photo de destination"
        verbose_name_plural = "photos de la destination"
