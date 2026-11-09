"""
Interactions utilisateurs : Avis (note 1–5 + modération) et Favoris.

Choix d'architecture (validé) : clés étrangères explicites nullables avec
une CheckConstraint en base garantissant qu'exactement UNE cible est
renseignée, et des UniqueConstraints conditionnelles empêchant les doublons.
Cela conserve l'intégrité référentielle SQL et permet des agrégations
directes (`SiteTouristique.objects.annotate(note_moyenne=Avg("avis__note"))`).
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.bookings.models import Reservation
from apps.circuits.models import Circuit
from apps.core.models import TimeStampedModel
from apps.guides.models import Guide
from apps.locations.models import Destination
from apps.tourism.models import SiteTouristique


class AvisQuerySet(models.QuerySet):
    def valides(self):
        return self.filter(statut_validation=Avis.StatutValidation.VALIDE)


class Avis(TimeStampedModel):
    class StatutValidation(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de modération"
        VALIDE = "valide", "Validé (publié)"
        REFUSE = "refuse", "Refusé"

    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.CASCADE,
        related_name="avis",
    )

    # Cibles possibles (exactement une doit être renseignée)
    site = models.ForeignKey(
        SiteTouristique,
        verbose_name="site touristique",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="avis",
    )
    circuit = models.ForeignKey(
        Circuit,
        verbose_name="circuit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="avis",
    )
    guide = models.ForeignKey(
        Guide,
        verbose_name="guide",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="avis",
    )

    reservation = models.ForeignKey(
        Reservation,
        verbose_name="réservation associée",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avis",
        help_text="Optionnel : permet d'afficher le badge « Voyageur vérifié ».",
    )

    note = models.PositiveSmallIntegerField(
        "note (sur 5)",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    titre = models.CharField("titre de l'avis", max_length=150, blank=True)
    commentaire = models.TextField("commentaire")
    statut_validation = models.CharField(
        "statut de validation",
        max_length=20,
        choices=StatutValidation.choices,
        default=StatutValidation.EN_ATTENTE,
    )
    date_validation = models.DateTimeField("validé le", null=True, blank=True)

    objects = AvisQuerySet.as_manager()

    class Meta:
        verbose_name = "avis"
        verbose_name_plural = "avis"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["statut_validation", "-created_at"], name="avis_validation_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(note__gte=1) & Q(note__lte=5),
                name="avis_note_entre_1_et_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(site__isnull=False, circuit__isnull=True, guide__isnull=True)
                    | Q(site__isnull=True, circuit__isnull=False, guide__isnull=True)
                    | Q(site__isnull=True, circuit__isnull=True, guide__isnull=False)
                ),
                name="avis_exactement_une_cible",
            ),
            models.UniqueConstraint(
                fields=["auteur", "site"],
                condition=Q(site__isnull=False),
                name="unique_avis_auteur_site",
            ),
            models.UniqueConstraint(
                fields=["auteur", "circuit"],
                condition=Q(circuit__isnull=False),
                name="unique_avis_auteur_circuit",
            ),
            models.UniqueConstraint(
                fields=["auteur", "guide"],
                condition=Q(guide__isnull=False),
                name="unique_avis_auteur_guide",
            ),
        ]

    def __str__(self):
        return f"Avis de {self.auteur} ({self.note}/5) sur {self.cible}"

    @property
    def cible(self):
        return self.site or self.circuit or self.guide

    @property
    def type_cible(self):
        if self.site_id:
            return "Site touristique"
        if self.circuit_id:
            return "Circuit"
        if self.guide_id:
            return "Guide"
        return "—"

    @property
    def est_verifie(self):
        return self.reservation_id is not None

    def clean(self):
        super().clean()
        cibles = [bool(self.site_id), bool(self.circuit_id), bool(self.guide_id)]
        if sum(cibles) != 1:
            raise ValidationError(
                "Sélectionnez exactement une cible pour l'avis (un site touristique, un circuit ou un guide)."
            )


class Favori(TimeStampedModel):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.CASCADE,
        related_name="favoris",
    )

    # Cibles possibles (exactement une doit être renseignée)
    destination = models.ForeignKey(
        Destination,
        verbose_name="destination",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favoris",
    )
    site = models.ForeignKey(
        SiteTouristique,
        verbose_name="site touristique",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favoris",
    )
    circuit = models.ForeignKey(
        Circuit,
        verbose_name="circuit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favoris",
    )
    guide = models.ForeignKey(
        Guide,
        verbose_name="guide",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favoris",
    )

    class Meta:
        verbose_name = "favori"
        verbose_name_plural = "favoris"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(destination__isnull=False, site__isnull=True, circuit__isnull=True, guide__isnull=True)
                    | Q(destination__isnull=True, site__isnull=False, circuit__isnull=True, guide__isnull=True)
                    | Q(destination__isnull=True, site__isnull=True, circuit__isnull=False, guide__isnull=True)
                    | Q(destination__isnull=True, site__isnull=True, circuit__isnull=True, guide__isnull=False)
                ),
                name="favori_exactement_une_cible",
            ),
            models.UniqueConstraint(
                fields=["utilisateur", "destination"],
                condition=Q(destination__isnull=False),
                name="unique_favori_user_destination",
            ),
            models.UniqueConstraint(
                fields=["utilisateur", "site"],
                condition=Q(site__isnull=False),
                name="unique_favori_user_site",
            ),
            models.UniqueConstraint(
                fields=["utilisateur", "circuit"],
                condition=Q(circuit__isnull=False),
                name="unique_favori_user_circuit",
            ),
            models.UniqueConstraint(
                fields=["utilisateur", "guide"],
                condition=Q(guide__isnull=False),
                name="unique_favori_user_guide",
            ),
        ]

    def __str__(self):
        return f"Favori de {self.utilisateur} → {self.cible}"

    @property
    def cible(self):
        return self.destination or self.site or self.circuit or self.guide

    @property
    def type_cible(self):
        if self.destination_id:
            return "Destination"
        if self.site_id:
            return "Site touristique"
        if self.circuit_id:
            return "Circuit"
        if self.guide_id:
            return "Guide"
        return "—"

    def clean(self):
        super().clean()
        cibles = [bool(self.destination_id), bool(self.site_id), bool(self.circuit_id), bool(self.guide_id)]
        if sum(cibles) != 1:
            raise ValidationError(
                "Sélectionnez exactement une cible pour le favori (destination, site, circuit ou guide)."
            )
