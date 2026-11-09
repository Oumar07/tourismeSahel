"""
Gestion des réservations de circuits et d'accompagnement par un guide.
"""
import secrets
import string
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.circuits.models import Circuit
from apps.core.models import TimeStampedModel
from apps.guides.models import Guide
from apps.locations.models import Pays

REFERENCE_ALPHABET = string.ascii_uppercase + string.digits


def generate_booking_reference():
    """
    Génère une référence unique lisible de la forme `TS-2026-A8F3K9`.
    """
    year = timezone.now().year
    while True:
        code = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
        reference = f"TS-{year}-{code}"
        if not Reservation.objects.filter(reference=reference).exists():
            return reference


class Reservation(TimeStampedModel):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ACCEPTEE = "acceptee", "Acceptée"
        REFUSEE = "refusee", "Refusée"
        ANNULEE = "annulee", "Annulée"
        TERMINEE = "terminee", "Terminée"

    reference = models.CharField(
        "référence",
        max_length=20,
        unique=True,
        editable=False,
        help_text="Générée automatiquement (ex : TS-2026-A8F3K9).",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="compte client",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reservations",
        help_text="Associé automatiquement si le visiteur est connecté.",
    )

    # Coordonnées du visiteur (conservées sur la réservation même sans compte)
    nom_visiteur = models.CharField("nom complet du visiteur", max_length=150)
    email_visiteur = models.EmailField("e-mail du visiteur")
    telephone_visiteur = models.CharField("téléphone du visiteur", max_length=30)
    pays_visiteur = models.ForeignKey(
        Pays,
        verbose_name="pays de résidence",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations_visiteurs",
    )

    # Prestation réservée
    circuit = models.ForeignKey(
        Circuit,
        verbose_name="circuit",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    guide = models.ForeignKey(
        Guide,
        verbose_name="guide accompagnateur",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reservations",
        help_text="Par défaut, le guide référent du circuit.",
    )
    date_depart = models.DateField("date de départ")
    date_fin = models.DateField(
        "date de fin",
        null=True,
        blank=True,
        help_text="Calculée automatiquement selon la durée du circuit si laissée vide.",
    )
    nombre_personnes = models.PositiveSmallIntegerField(
        "nombre de voyageurs",
        default=1,
        validators=[MinValueValidator(1)],
    )

    # Tarification figée au moment de la réservation
    prix_unitaire = models.DecimalField(
        "tarif par personne figé (FCFA)",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        blank=True,
        help_text="Copié automatiquement depuis le tarif du circuit si laissé vide.",
    )
    montant_total = models.DecimalField(
        "montant total (FCFA)",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        blank=True,
    )

    # Suivi & traitement
    statut = models.CharField(
        "statut",
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    demandes_speciales = models.TextField(
        "demandes particulières",
        blank=True,
        help_text="Régime alimentaire, besoins d'accessibilité, souhaits particuliers…",
    )
    motif_refus_ou_annulation = models.TextField(
        "motif de refus ou d'annulation",
        blank=True,
    )
    date_reponse = models.DateTimeField("traitée le", null=True, blank=True)

    class Meta:
        verbose_name = "réservation"
        verbose_name_plural = "réservations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["statut", "date_depart"], name="reservation_statut_depart_idx"),
            models.Index(fields=["utilisateur", "-created_at"], name="reservation_user_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nombre_personnes__gte=1),
                name="reservation_nb_personnes_positif",
            ),
            models.CheckConstraint(
                condition=models.Q(prix_unitaire__gte=0) & models.Q(montant_total__gte=0),
                name="reservation_montants_positifs",
            ),
        ]

    def __str__(self):
        return f"{self.reference} — {self.nom_visiteur} ({self.circuit})"

    def clean(self):
        super().clean()
        if self.circuit_id and self.nombre_personnes:
            if self.nombre_personnes < self.circuit.participants_min:
                raise ValidationError(
                    {
                        "nombre_personnes": (
                            f"Ce circuit requiert au minimum {self.circuit.participants_min} participant(s)."
                        )
                    }
                )
            if self.nombre_personnes > self.circuit.participants_max:
                raise ValidationError(
                    {
                        "nombre_personnes": (
                            f"Ce circuit est limité à {self.circuit.participants_max} participant(s)."
                        )
                    }
                )
        if self.date_depart and self.date_fin and self.date_fin < self.date_depart:
            raise ValidationError({"date_fin": "La date de fin ne peut pas précéder la date de départ."})

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_booking_reference()
        if self.circuit_id:
            if self.guide_id is None and self.circuit.guide_referent_id:
                self.guide_id = self.circuit.guide_referent_id
            if self.prix_unitaire is None:
                self.prix_unitaire = self.circuit.tarif_par_personne
            if self.date_depart and not self.date_fin:
                self.date_fin = self.date_depart + timedelta(days=max(self.circuit.duree_jours - 1, 0))
        if self.prix_unitaire is not None and self.nombre_personnes:
            self.montant_total = self.prix_unitaire * Decimal(self.nombre_personnes)
        super().save(*args, **kwargs)
