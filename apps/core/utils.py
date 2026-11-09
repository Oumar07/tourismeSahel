"""Utilitaires partagés par toutes les applications TourismeSahel."""
import uuid
from pathlib import Path

from django.utils.deconstruct import deconstructible
from django.utils.text import slugify


def generate_unique_slug(instance, value, slug_field_name="slug"):
    """
    Construit un slug unique pour `instance` à partir de `value`.

    "Mosquée de Djenné" -> "mosquee-de-djenne", puis "mosquee-de-djenne-2"
    si le slug existe déjà. Les accents sont translittérés par slugify().
    """
    model = type(instance)
    max_length = model._meta.get_field(slug_field_name).max_length

    base_slug = slugify(value)[:max_length].strip("-") or "element"
    queryset = model._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    slug = base_slug
    counter = 2
    while queryset.filter(**{slug_field_name: slug}).exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug


@deconstructible
class UploadToPath:
    """
    Chemin d'upload propre, lisible et sans collision :

        <prefix>/<slug-de-l-objet>/<identifiant-aleatoire>.<extension>
        ex. "tourism/sites/mosquee-de-djenne/3f9a1c0b7e2d.jpg"

    `slug_attr` peut traverser une relation, ex. "site.slug" pour une photo
    rangée dans le dossier de son site.

    @deconstructible permet à Django de sérialiser cet objet dans les
    migrations (une lambda ne le permettrait pas).
    """

    def __init__(self, prefix, slug_attr="slug"):
        self.prefix = prefix.strip("/")
        self.slug_attr = slug_attr

    def __call__(self, instance, filename):
        value = instance
        for attr_name in self.slug_attr.split("."):
            value = getattr(value, attr_name, None)
            if value is None:
                break

        folder = slugify(str(value)) if value else "divers"
        extension = Path(filename).suffix.lower() or ".jpg"
        return f"{self.prefix}/{folder}/{uuid.uuid4().hex[:12]}{extension}"
