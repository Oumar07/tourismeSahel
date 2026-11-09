"""Helpers d'affichage pour l'interface d'administration."""
from django.utils.html import format_html


def image_thumbnail(image_field, height=48):
    """Miniature HTML sécurisée d'un ImageField (ou un tiret si vide)."""
    if not image_field:
        return "—"
    return format_html(
        '<img src="{}" alt="" style="height:{}px;width:auto;max-width:160px;'
        'object-fit:cover;border-radius:6px;">',
        image_field.url,
        height,
    )
