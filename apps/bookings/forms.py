from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.forms import BootstrapFormMixin
from apps.circuits.models import Circuit
from apps.guides.models import Guide
from apps.locations.models import Pays

from .models import Reservation


class ReservationForm(BootstrapFormMixin, forms.ModelForm):
    """
    Formulaire de demande de réservation avec validations métier :
    - Date de départ dans le futur (>= aujourd'hui)
    - Nombre de voyageurs compris entre le minimum et le maximum du circuit
    - Vérification de la disponibilité du guide sur la période du séjour
    """

    date_depart = forms.DateField(
        label="Date de départ souhaitée",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Reservation
        fields = (
            "circuit",
            "guide",
            "date_depart",
            "nombre_personnes",
            "nom_visiteur",
            "email_visiteur",
            "telephone_visiteur",
            "pays_visiteur",
            "demandes_speciales",
        )
        widgets = {
            "demandes_speciales": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Régime alimentaire particulier, besoin d'accessibilité, souhaits d'étapes…",
                }
            ),
        }

    def __init__(self, *args, user=None, initial_circuit=None, initial_guide=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["circuit"].queryset = Circuit.objects.actifs().select_related("destination_depart", "guide_referent")
        self.fields["guide"].queryset = Guide.objects.verifies()
        self.fields["guide"].empty_label = "Guide référent du circuit (par défaut)"
        self.fields["pays_visiteur"].queryset = Pays.objects.actifs().order_by("nom")
        self.fields["pays_visiteur"].empty_label = "Sélectionnez votre pays de résidence"

        # Date minimale dans le sélecteur HTML5
        aujourd_hui = timezone.localdate()
        self.fields["date_depart"].widget.attrs["min"] = aujourd_hui.isoformat()

        # Pré-remplissage du circuit et de son guide référent
        if initial_circuit and not self.is_bound:
            self.initial.setdefault("circuit", initial_circuit.pk)
            self.initial.setdefault("nombre_personnes", initial_circuit.participants_min)
            if initial_circuit.guide_referent_id and initial_circuit.guide_referent.est_verifie:
                self.initial.setdefault("guide", initial_circuit.guide_referent_id)
        if initial_guide and not self.is_bound:
            self.initial["guide"] = initial_guide.pk

        # Pré-remplissage des coordonnées si l'utilisateur est connecté
        if user and getattr(user, "is_authenticated", False) and not self.is_bound:
            nom_complet = f"{user.first_name} {user.last_name}".strip() or user.username
            self.initial.setdefault("nom_visiteur", nom_complet)
            self.initial.setdefault("email_visiteur", user.email)
            self.initial.setdefault("telephone_visiteur", getattr(user, "telephone", ""))
            if getattr(user, "pays_origine_id", None):
                self.initial.setdefault("pays_origine", user.pays_origine_id)
                self.initial.setdefault("pays_visiteur", user.pays_origine_id)

        self._apply_bootstrap_classes()
        self.fields["nom_visiteur"].widget.attrs["placeholder"] = "Prénom et nom"
        self.fields["email_visiteur"].widget.attrs["placeholder"] = "vous@exemple.com"
        self.fields["telephone_visiteur"].widget.attrs["placeholder"] = "+221 77 000 00 00"

    def clean_date_depart(self):
        date_depart = self.cleaned_data.get("date_depart")
        if date_depart and date_depart < timezone.localdate():
            raise ValidationError("La date de départ ne peut pas être située dans le passé.")
        return date_depart

    def clean(self):
        cleaned_data = super().clean()
        circuit = cleaned_data.get("circuit")
        guide = cleaned_data.get("guide")
        date_depart = cleaned_data.get("date_depart")
        nombre_personnes = cleaned_data.get("nombre_personnes")

        if circuit and nombre_personnes:
            if nombre_personnes < circuit.participants_min:
                self.add_error(
                    "nombre_personnes",
                    f"Ce circuit nécessite au minimum {circuit.participants_min} participant(s).",
                )
            elif nombre_personnes > circuit.participants_max:
                self.add_error(
                    "nombre_personnes",
                    f"Ce circuit est limité à {circuit.participants_max} participant(s) par départ.",
                )

        if circuit and date_depart:
            date_fin = date_depart + timedelta(days=max(circuit.duree_jours - 1, 0))
            guide_effectif = guide or circuit.guide_referent
            if guide_effectif and not guide_effectif.est_disponible_sur_periode(date_depart, date_fin):
                self.add_error(
                    "date_depart",
                    f"Le guide {guide_effectif.nom_complet} n'est pas disponible du "
                    f"{date_depart.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}. "
                    "Veuillez choisir une autre date ou un autre guide.",
                )

        return cleaned_data

