from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from apps.locations.models import Pays

User = get_user_model()


class BootstrapFormMixin:
    """Applique automatiquement les classes CSS Bootstrap 5 / TourismeSahel aux champs."""

    def _apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class InscriptionForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(label="Prénom", max_length=150, required=True)
    last_name = forms.CharField(label="Nom", max_length=150, required=True)
    email = forms.EmailField(label="Adresse e-mail", required=True)
    telephone = forms.CharField(label="Téléphone", max_length=30, required=False)
    pays_origine = forms.ModelChoiceField(
        label="Pays de résidence / d'origine",
        queryset=Pays.objects.actifs().order_by("nom"),
        required=False,
        empty_label="Sélectionnez un pays (optionnel)",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "telephone",
            "pays_origine",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()
        self.fields["username"].widget.attrs["placeholder"] = "Ex : fatou_ndiaye"
        self.fields["first_name"].widget.attrs["placeholder"] = "Votre prénom"
        self.fields["last_name"].widget.attrs["placeholder"] = "Votre nom"
        self.fields["email"].widget.attrs["placeholder"] = "vous@exemple.com"
        self.fields["telephone"].widget.attrs["placeholder"] = "+221 77 000 00 00"

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return email


class ConnexionForm(BootstrapFormMixin, AuthenticationForm):
    """Permet de se connecter avec son nom d'utilisateur OU son adresse e-mail."""

    username = forms.CharField(
        label="Nom d'utilisateur ou adresse e-mail",
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Votre identifiant ou e-mail"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "••••••••"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()

    def clean_username(self):
        identifiant = self.cleaned_data.get("username", "").strip()
        if "@" in identifiant:
            user = User.objects.filter(email__iexact=identifiant).only("username").first()
            if user:
                return user.username
        return identifiant


class ProfilForm(BootstrapFormMixin, forms.ModelForm):
    """Formulaire de mise à jour du profil depuis l'espace visiteur."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "telephone", "pays_origine", "avatar")
        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "email": "Adresse e-mail",
            "telephone": "Téléphone",
            "pays_origine": "Pays d'origine",
            "avatar": "Photo de profil",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pays_origine"].queryset = Pays.objects.actifs().order_by("nom")
        self._apply_bootstrap_classes()

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Cette adresse e-mail est déjà utilisée par un autre compte.")
        return email

