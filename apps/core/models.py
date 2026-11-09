"""
Modèles abstraits réutilisés par toutes les applications.
Aucune table n'est créée pour ce fichier (abstract = True).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .utils import generate_unique_slug


class ActiveQuerySet(models.QuerySet):
    """Permet d'écrire `Destination.objects.actifs()` dans les vues."""

    def actifs(self):
        return self.filter(est_actif=True)


class TimeStampedModel(models.Model):
    """Ajoute les dates de création et de dernière modification."""

    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class SluggedModel(models.Model):
    """
    Ajoute un slug unique, généré automatiquement depuis le champ
    `slug_source_field` (par défaut "nom") s'il est laissé vide.
    """

    slug = models.SlugField(
        "slug (URL)",
        max_length=160,
        unique=True,
        blank=True,
        help_text="Laissez vide pour le générer automatiquement à partir du nom.",
    )

    slug_source_field = "nom"

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, getattr(self, self.slug_source_field))
        super().save(*args, **kwargs)


class GeoPointModel(models.Model):
    """Coordonnées GPS (WGS84, degrés décimaux, précision ~10 cm)."""

    latitude = models.DecimalField(
        "latitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
        help_text="Ex : 13.905600 (Djenné)",
    )
    longitude = models.DecimalField(
        "longitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
        help_text="Ex : -4.555600 (Djenné)",
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError("Renseignez à la fois la latitude et la longitude, ou aucune des deux.")

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def google_maps_url(self):
        if not self.has_coordinates:
            return ""
        return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"


class BasePhoto(TimeStampedModel):
    """
    Champs communs aux photos de galerie. Chaque modèle concret ajoute
    son champ `image` (avec son propre upload_to) et sa ForeignKey.
    """

    legende = models.CharField("légende", max_length=200, blank=True)
    credit_photo = models.CharField("crédit photo", max_length=120, blank=True)
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)

    class Meta:
        abstract = True
        ordering = ["ordre", "pk"]

    def __str__(self):
        return self.legende or f"Photo n°{self.pk}"
