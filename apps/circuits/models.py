"""
Circuits touristiques et leur programme jour par jour.

La relation ManyToMany `Circuit.sites` passe par `EtapeCircuit` (`through=`) :
chaque étape précise le jour, l'ordre de passage, l'intitulé et le détail
des activités. Un même site peut ainsi apparaître à plusieurs étapes d'un
circuit long si besoin, tandis que l'ordre au sein d'un circuit reste unique.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import ActiveQuerySet, SluggedModel, TimeStampedModel
from apps.core.utils import UploadToPath
from apps.guides.models import Guide
from apps.locations.models import Destination
from apps.tourism.models import SiteTouristique


class Circuit(TimeStampedModel, SluggedModel):
    class Difficulte(models.TextChoices):
        FACILE = "facile", "Facile — accessible à tous"
        MODERE = "modere", "Modéré — marche régulière"
        SPORTIF = "sportif", "Sportif — bonne condition physique"

    titre = models.CharField("titre", max_length=160)
    description_courte = models.CharField(
        "accroche",
        max_length=255,
        help_text="Une ou deux phrases affichées sur les cartes de la liste.",
    )
    description = models.TextField("présentation générale")
    programme_detaille = models.TextField(
        "programme détaillé",
        blank=True,
        help_text="Synthèse du déroulé jour par jour (complète les étapes structurées ci-dessous).",
    )
    destination_depart = models.ForeignKey(
        Destination,
        verbose_name="destination de départ",
        on_delete=models.PROTECT,
        related_name="circuits_au_depart",
    )
    guide_referent = models.ForeignKey(
        Guide,
        verbose_name="guide référent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="circuits",
    )
    sites = models.ManyToManyField(
        SiteTouristique,
        through="EtapeCircuit",
        verbose_name="sites visités",
        related_name="circuits",
    )
    duree_jours = models.PositiveSmallIntegerField(
        "durée (jours)",
        default=1,
        validators=[MinValueValidator(1)],
    )
    tarif_par_personne = models.DecimalField(
        "tarif par personne (FCFA)",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    participants_min = models.PositiveSmallIntegerField(
        "nombre minimum de participants",
        default=1,
        validators=[MinValueValidator(1)],
    )
    participants_max = models.PositiveSmallIntegerField(
        "nombre maximum de participants",
        default=12,
        validators=[MinValueValidator(1)],
    )
    difficulte = models.CharField(
        "niveau de difficulté",
        max_length=20,
        choices=Difficulte.choices,
        default=Difficulte.FACILE,
    )
    inclus = models.TextField(
        "ce qui est inclus",
        blank=True,
        help_text="Un élément par ligne (transport, hébergement, repas, entrées…).",
    )
    non_inclus = models.TextField(
        "ce qui n'est pas inclus",
        blank=True,
        help_text="Un élément par ligne (vols internationaux, boissons, pourboires…).",
    )
    conseils_equipement = models.TextField("équipement conseillé", blank=True)
    image_principale = models.ImageField(
        "image principale",
        upload_to=UploadToPath("circuits/couvertures"),
    )
    en_vedette = models.BooleanField("mis en avant sur l'accueil", default=False)
    est_actif = models.BooleanField("publié", default=True)

    slug_source_field = "titre"
    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "circuit"
        verbose_name_plural = "circuits"
        ordering = ["titre"]
        indexes = [
            models.Index(fields=["est_actif", "en_vedette"], name="circuit_publication_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duree_jours__gte=1),
                name="circuit_duree_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(tarif_par_personne__gte=0),
                name="circuit_tarif_positif",
            ),
            models.CheckConstraint(
                condition=models.Q(participants_max__gte=models.F("participants_min")),
                name="circuit_participants_max_gte_min",
            ),
        ]

    def __str__(self):
        return self.titre

    def clean(self):
        super().clean()
        if self.participants_min and self.participants_max and self.participants_max < self.participants_min:
            raise ValidationError(
                {"participants_max": "Le maximum de participants doit être supérieur ou égal au minimum."}
            )

    @property
    def pays(self):
        return self.destination_depart.region.pays


class EtapeCircuit(TimeStampedModel):
    circuit = models.ForeignKey(
        Circuit,
        verbose_name="circuit",
        on_delete=models.CASCADE,
        related_name="etapes",
    )
    site = models.ForeignKey(
        SiteTouristique,
        verbose_name="site visité",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="etapes_circuit",
        help_text="Laissez vide si l'étape correspond à un trajet ou une journée libre.",
    )
    jour = models.PositiveSmallIntegerField(
        "jour",
        default=1,
        validators=[MinValueValidator(1)],
    )
    ordre = models.PositiveSmallIntegerField(
        "ordre dans le circuit",
        default=1,
        validators=[MinValueValidator(1)],
    )
    titre = models.CharField("intitulé de l'étape", max_length=160)
    description = models.TextField("programme de l'étape", blank=True)
    hebergement = models.CharField("hébergement prévu", max_length=150, blank=True)
    repas_inclus = models.CharField(
        "repas inclus",
        max_length=100,
        blank=True,
        help_text="Ex : Petit-déjeuner, déjeuner, dîner au bivouac",
    )

    class Meta:
        verbose_name = "étape de circuit"
        verbose_name_plural = "étapes du circuit"
        ordering = ["jour", "ordre", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["circuit", "ordre"],
                name="unique_ordre_etape_par_circuit",
            ),
        ]

    def __str__(self):
        return f"Jour {self.jour} (#{self.ordre}) — {self.titre}"
