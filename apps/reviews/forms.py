from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.forms import BootstrapFormMixin

from .models import Avis


class AvisForm(BootstrapFormMixin, forms.ModelForm):
    """Formulaire de dépôt d'un avis (note de 1 à 5 étoiles, titre et commentaire)."""

    CHOIX_NOTES = [
        (5, "5 ★ — Exceptionnel"),
        (4, "4 ★ — Très bien"),
        (3, "3 ★ — Bien"),
        (2, "2 ★ — Moyen"),
        (1, "1 ★ — Décevant"),
    ]

    note = forms.TypedChoiceField(
        label="Votre note",
        choices=CHOIX_NOTES,
        coerce=int,
        initial=5,
    )

    class Meta:
        model = Avis
        fields = ("note", "titre", "commentaire")
        widgets = {
            "titre": forms.TextInput(attrs={"placeholder": "En quelques mots (ex : Une visite inoubliable au lever du soleil)"}),
            "commentaire": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Partagez votre expérience, vos conseils pratiques et ce qui vous a marqué…",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()

    def clean_commentaire(self):
        commentaire = self.cleaned_data.get("commentaire", "").strip()
        if len(commentaire) < 10:
            raise ValidationError("Votre commentaire doit contenir au moins 10 caractères.")
        return commentaire

