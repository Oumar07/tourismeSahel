from django.contrib import admin
from django.db.models import Count

from apps.core.admin_utils import image_thumbnail

from .models import CategorieSite, PhotoSite, SiteTouristique


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------
@admin.register(CategorieSite)
class CategorieSiteAdmin(admin.ModelAdmin):
    list_display = ("nom", "famille", "icone", "nombre_sites", "ordre")
    list_editable = ("ordre",)
    list_filter = ("famille",)
    search_fields = ("nom",)
    prepopulated_fields = {"slug": ("nom",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nombre_sites=Count("sites"))

    @admin.display(description="Sites", ordering="_nombre_sites")
    def nombre_sites(self, obj):
        return obj._nombre_sites


# ---------------------------------------------------------------------------
# Sites touristiques
# ---------------------------------------------------------------------------
class PhotoSiteInline(admin.TabularInline):
    model = PhotoSite
    fields = ("apercu", "image", "legende", "credit_photo", "ordre")
    readonly_fields = ("apercu",)
    extra = 1

    @admin.display(description="Aperçu")
    def apercu(self, obj):
        return image_thumbnail(obj.image, height=60)


@admin.register(SiteTouristique)
class SiteTouristiqueAdmin(admin.ModelAdmin):
    list_display = (
        "apercu_liste",
        "nom",
        "destination",
        "categorie",
        "prix_entree",
        "patrimoine_unesco",
        "en_vedette",
        "est_actif",
    )
    list_display_links = ("apercu_liste", "nom")
    list_editable = ("en_vedette", "est_actif")
    list_filter = (
        "categorie__famille",
        "categorie",
        "destination__region__pays",
        "patrimoine_unesco",
        "en_vedette",
        "est_actif",
    )
    list_select_related = ("destination", "categorie")
    search_fields = ("nom", "description_courte", "destination__nom")
    autocomplete_fields = ("destination", "categorie")
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("apercu_image", "created_at", "updated_at")
    inlines = [PhotoSiteInline]
    fieldsets = (
        (None, {"fields": ("destination", "categorie", "nom", "slug")}),
        ("Contenu", {"fields": ("description_courte", "description", "histoire")}),
        ("Image principale", {"fields": (("image_principale", "apercu_image"),)}),
        (
            "Infos pratiques",
            {"fields": ("adresse", "horaires_ouverture", ("prix_entree", "duree_visite_minutes"), "patrimoine_unesco")},
        ),
        ("Localisation GPS", {"fields": (("latitude", "longitude"),)}),
        ("Publication", {"fields": ("en_vedette", "est_actif")}),
        ("Suivi", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Image")
    def apercu_liste(self, obj):
        return image_thumbnail(obj.image_principale, height=40)

    @admin.display(description="Aperçu")
    def apercu_image(self, obj):
        return image_thumbnail(obj.image_principale, height=140)
