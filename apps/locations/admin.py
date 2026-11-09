from django.contrib import admin
from django.db.models import Count

from apps.core.admin_utils import image_thumbnail

from .models import Destination, Pays, PhotoDestination, Region


# ---------------------------------------------------------------------------
# Pays
# ---------------------------------------------------------------------------
class RegionInline(admin.TabularInline):
    model = Region
    fields = ("nom", "chef_lieu", "est_actif")
    extra = 0
    show_change_link = True


@admin.register(Pays)
class PaysAdmin(admin.ModelAdmin):
    list_display = ("apercu_drapeau", "nom", "code_iso", "capitale", "nombre_regions", "est_actif")
    list_display_links = ("apercu_drapeau", "nom")
    list_editable = ("est_actif",)
    list_filter = ("est_actif",)
    search_fields = ("nom", "code_iso", "capitale")
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("apercu_drapeau", "apercu_couverture", "created_at", "updated_at")
    inlines = [RegionInline]
    fieldsets = (
        (None, {"fields": ("nom", "slug", "code_iso", "est_actif")}),
        ("Informations pratiques", {"fields": ("capitale", "devise", "langues_officielles", "description")}),
        ("Visuels", {"fields": (("drapeau", "apercu_drapeau"), ("image_couverture", "apercu_couverture"))}),
        ("Suivi", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nombre_regions=Count("regions"))

    @admin.display(description="Drapeau")
    def apercu_drapeau(self, obj):
        return image_thumbnail(obj.drapeau, height=28)

    @admin.display(description="Aperçu")
    def apercu_couverture(self, obj):
        return image_thumbnail(obj.image_couverture, height=120)

    @admin.display(description="Régions", ordering="_nombre_regions")
    def nombre_regions(self, obj):
        return obj._nombre_regions


# ---------------------------------------------------------------------------
# Région
# ---------------------------------------------------------------------------
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("nom", "pays", "chef_lieu", "nombre_destinations", "est_actif")
    list_editable = ("est_actif",)
    list_filter = ("pays", "est_actif")
    list_select_related = ("pays",)
    search_fields = ("nom", "chef_lieu", "pays__nom")
    autocomplete_fields = ("pays",)
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("apercu_image", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("pays", "nom", "slug", "chef_lieu", "est_actif")}),
        ("Présentation", {"fields": ("description", ("image", "apercu_image"))}),
        ("Suivi", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nombre_destinations=Count("destinations"))

    @admin.display(description="Aperçu")
    def apercu_image(self, obj):
        return image_thumbnail(obj.image, height=120)

    @admin.display(description="Destinations", ordering="_nombre_destinations")
    def nombre_destinations(self, obj):
        return obj._nombre_destinations


# ---------------------------------------------------------------------------
# Destination
# ---------------------------------------------------------------------------
class PhotoDestinationInline(admin.TabularInline):
    model = PhotoDestination
    fields = ("apercu", "image", "legende", "credit_photo", "ordre")
    readonly_fields = ("apercu",)
    extra = 1

    @admin.display(description="Aperçu")
    def apercu(self, obj):
        return image_thumbnail(obj.image, height=60)


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("apercu_liste", "nom", "region", "pays", "en_vedette", "est_actif")
    list_display_links = ("apercu_liste", "nom")
    list_editable = ("en_vedette", "est_actif")
    list_filter = ("region__pays", "en_vedette", "est_actif")
    list_select_related = ("region__pays",)
    search_fields = ("nom", "description_courte", "region__nom", "region__pays__nom")
    autocomplete_fields = ("region",)
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("apercu_image", "created_at", "updated_at")
    inlines = [PhotoDestinationInline]
    fieldsets = (
        (None, {"fields": ("region", "nom", "slug")}),
        ("Contenu", {"fields": ("description_courte", "description", "meilleure_periode")}),
        ("Image principale", {"fields": (("image_principale", "apercu_image"),)}),
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

    @admin.display(description="Pays", ordering="region__pays__nom")
    def pays(self, obj):
        return obj.region.pays
