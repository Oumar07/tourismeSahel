"""
Utilisateur personnalisé pour TourismeSahel.

Important : `AUTH_USER_MODEL = "accounts.User"` doit être déclaré dans
`settings.py` AVANT le tout premier `python manage.py migrate`.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.utils import UploadToPath


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        TOURISTE = "touriste", "Touriste"
        GUIDE = "guide", "Guide"
        ADMIN = "admin", "Administrateur"

    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField(
        "rôle",
        max_length=20,
        choices=Role.choices,
        default=Role.TOURISTE,
    )
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    avatar = models.ImageField(
        "photo de profil",
        upload_to=UploadToPath("accounts/avatars", slug_attr="username"),
        blank=True,
    )
    pays_origine = models.ForeignKey(
        "locations.Pays",
        verbose_name="pays d'origine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utilisateurs",
    )

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def est_guide(self):
        return self.role == self.Role.GUIDE or hasattr(self, "guide_profile")
