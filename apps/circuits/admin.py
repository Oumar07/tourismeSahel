from django.contrib import admin
from django.db.models import Count

from apps.core.admin_utils import image_thumbnail

from .models import Circuit, EtapeCircuit


class EtapeCircuitInline(admin.StackedInline):
    model = EtapeCircuit
    fields = (("jour", "ordre", "site"), "titre", "description", ("hebergement", "repas_inclus"))
    autocomplete_fields = ("site",)
    extra = 1


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = (
        "apercu_liste",
        "titre",
        "destination_depart",
        "guide_referent",
        "duree_jours",
        "tarif_par_personne",
        "difficulte",
        "nombre_etapes",
        "en_vedette",
        "est_actif",
    )
    list_display_links = ("apercu_liste", "titre")
    list_editable = ("en_vedette", "est_actif")
    list_filter = (
        "difficulte",
        "destination_depart__region__pays",
        "en_vedette",
        "est_actif",
    )
    list_select_related = ("destination_depart", "guide_referent")
    search_fields = ("titre", "description_courte", "destination_depart__nom", "guide_referent__nom_complet")
    autocomplete_fields = ("destination_depart", "guide_referent")
    prepopulated_fields = {"slug": ("titre",)}
    readonly_fields = ("apercu_image", "created_at", "updated_at")
    inlines = [EtapeCircuitInline]
    fieldsets = (
        (None, {"fields": ("titre", "slug", "destination_depart", "guide_referent")}),
        ("Présentation & programme", {"fields": ("description_courte", "description", "programme_detaille")}),
        ("Image principale", {"fields": (("image_principale", "apercu_image"),)}),
        (
            "Durée, tarif & groupe",
            {"fields": (("duree_jours", "difficulte"), "tarif_par_personne", ("participants_min", "participants_max"))},
        ),
        ("Informations pratiques", {"fields": ("inclus", "non_inclus", "conseils_equipement")}),
        ("Publication", {"fields": ("en_vedette", "est_actif")}),
        ("Suivi", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_nombre_etapes=Count("etapes"))

    @admin.display(description="Image")
    def apercu_liste(self, obj):
        return image_thumbnail(obj.image_principale, height=40)

    @admin.display(description="Aperçu")
    def apercu_image(self, obj):
        return image_thumbnail(obj.image_principale, height=140)

    @admin.display(description="Étapes", ordering="_nombre_etapes")
    def nombre_etapes(self, obj):
        return obj._nombre_etapes
