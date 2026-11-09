"""
Profils de guides touristiques, langues parlées, spécialités et périodes
de disponibilité ou d'indisponibilité.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import ActiveQuerySet, SluggedModel, TimeStampedModel
from apps.core.utils import UploadToPath
from apps.locations.models import Region


class Langue(TimeStampedModel):
    code = models.CharField(
        "code",
        max_length=10,
        unique=True,
        help_text="Code court, ex : fr, en, wo (wolof), bm (bambara), ha (haoussa), ff (peul).",
    )
    nom = models.CharField("nom", max_length=80, unique=True)

    class Meta:
        verbose_name = "langue"
        verbose_name_plural = "langues"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class SpecialiteGuide(TimeStampedModel, SluggedModel):
    nom = models.CharField("nom", max_length=100, unique=True)
    description = models.TextField("description", blank=True)
    icone = models.CharField(
        "icône",
        max_length=50,
        blank=True,
        help_text="Classe Bootstrap Icons, ex : bi-compass, bi-camera, bi-Tree",
    )

    class Meta:
        verbose_name = "spécialité de guide"
        verbose_name_plural = "spécialités de guides"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class GuideQuerySet(ActiveQuerySet):
    def verifies(self):
        return self.filter(statut_verification=Guide.StatutVerification.VERIFIE, est_actif=True)


class Guide(TimeStampedModel, SluggedModel):
    class StatutVerification(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de vérification"
        VERIFIE = "verifie", "Vérifié"
        REFUSE = "refuse", "Refusé"
        SUSPENDU = "suspendu", "Suspendu"

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="compte utilisateur",
        on_delete=models.CASCADE,
        related_name="guide_profile",
    )
    nom_complet = models.CharField(
        "nom affiché",
        max_length=150,
        help_text="Nom public du guide (sert aussi à générer l'URL de sa fiche).",
    )
    titre_professionnel = models.CharField(
        "titre professionnel",
        max_length=150,
        blank=True,
        help_text="Ex : Guide national certifié — spécialiste du Pays Dogon",
    )
    bio = models.TextField("biographie")
    photo = models.ImageField(
        "photo",
        upload_to=UploadToPath("guides/photos"),
        blank=True,
    )
    langues = models.ManyToManyField(
        Langue,
        verbose_name="langues parlées",
        related_name="guides",
    )
    specialites = models.ManyToManyField(
        SpecialiteGuide,
        verbose_name="spécialités",
        related_name="guides",
        blank=True,
    )
    regions = models.ManyToManyField(
        Region,
        verbose_name="régions d'intervention",
        related_name="guides",
        blank=True,
    )
    annees_experience = models.PositiveSmallIntegerField("années d'expérience", default=0)
    tarif_journalier = models.DecimalField(
        "tarif journalier indicatif (FCFA)",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    numero_licence = models.CharField(
        "numéro de carte / licence professionnelle",
        max_length=80,
        unique=True,
        null=True,
        blank=True,
    )
    document_justificatif = models.FileField(
        "justificatif professionnel",
        upload_to=UploadToPath("guides/justificatifs"),
        blank=True,
        help_text="Scan de la carte de guide ou attestation (visible uniquement par l'administration).",
    )
    statut_verification = models.CharField(
        "statut de vérification",
        max_length=20,
        choices=StatutVerification.choices,
        default=StatutVerification.EN_ATTENTE,
    )
    date_verification = models.DateTimeField("vérifié le", null=True, blank=True)
    commentaire_moderation = models.TextField(
        "motif / note interne",
        blank=True,
        help_text="Explication en cas de refus ou de suspension.",
    )
    en_vedette = models.BooleanField("mis en avant sur l'accueil", default=False)
    est_actif = models.BooleanField("profil visible", default=True)

    slug_source_field = "nom_complet"
    objects = GuideQuerySet.as_manager()

    class Meta:
        verbose_name = "guide"
        verbose_name_plural = "guides"
        ordering = ["nom_complet"]
        indexes = [
            models.Index(fields=["statut_verification", "est_actif"], name="guide_verification_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tarif_journalier__gte=0),
                name="guide_tarif_positif",
            ),
        ]

    def __str__(self):
        return self.nom_complet

    @property
    def est_verifie(self):
        return self.statut_verification == self.StatutVerification.VERIFIE

    def est_disponible_sur_periode(self, date_debut, date_fin):
        """
        Indique si le guide est disponible entre `date_debut` et `date_fin` :
        son profil doit être actif et vérifié, et aucune période marquée
        INDISPONIBLE ou RESERVEE ne doit chevaucher ces dates.
        """
        if not (self.est_actif and self.est_verifie):
            return False
        indisponibilites = self.disponibilites.exclude(
            statut=DisponibiliteGuide.Statut.DISPONIBLE,
        ).filter(
            date_debut__lte=date_fin,
            date_fin__gte=date_debut,
        )
        return not indisponibilites.exists()


class DisponibiliteGuide(TimeStampedModel):
    class Statut(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        INDISPONIBLE = "indisponible", "Indisponible (congés, mission externe…)"
        RESERVE = "reserve", "Réservé sur un circuit"

    guide = models.ForeignKey(
        Guide,
        verbose_name="guide",
        on_delete=models.CASCADE,
        related_name="disponibilites",
    )
    date_debut = models.DateField("date de début")
    date_fin = models.DateField("date de fin")
    statut = models.CharField(
        "statut",
        max_length=20,
        choices=Statut.choices,
        default=Statut.DISPONIBLE,
    )
    note = models.CharField("précision", max_length=200, blank=True)

    class Meta:
        verbose_name = "disponibilité de guide"
        verbose_name_plural = "disponibilités des guides"
        ordering = ["date_debut", "date_fin"]
        indexes = [
            models.Index(fields=["guide", "date_debut", "date_fin"], name="dispo_guide_periode_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_fin__gte=models.F("date_debut")),
                name="dispo_date_fin_apres_debut",
            ),
        ]

    def __str__(self):
        return f"{self.guide} — du {self.date_debut} au {self.date_fin} ({self.get_statut_display()})"

    def clean(self):
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin doit être postérieure ou égale à la date de début."})
