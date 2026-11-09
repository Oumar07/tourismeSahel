from django.contrib import admin
from django.utils import timezone

from .models import Avis, Favori


@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = (
        "auteur",
        "type_cible",
        "cible",
        "note",
        "est_verifie",
        "statut_validation",
        "created_at",
    )
    list_filter = ("statut_validation", "note", "created_at")
    list_select_related = ("auteur", "site", "circuit", "guide", "reservation")
    search_fields = ("auteur__username", "auteur__email", "titre", "commentaire")
    autocomplete_fields = ("auteur", "site", "circuit", "guide", "reservation")
    readonly_fields = ("date_validation", "created_at", "updated_at")
    actions = ["valider_avis", "refuser_avis"]
    fieldsets = (
        ("Auteur & réservation", {"fields": ("auteur", "reservation")}),
        (
            "Objet évalué (en renseigner un seul)",
            {"fields": ("site", "circuit", "guide")},
        ),
        ("Contenu de l'avis", {"fields": ("note", "titre", "commentaire")}),
        ("Modération", {"fields": (("statut_validation", "date_validation"),)}),
        ("Horodatage", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Type")
    def type_cible(self, obj):
        return obj.type_cible

    @admin.display(description="Cible")
    def cible(self, obj):
        return obj.cible

    @admin.display(description="Vérifié", boolean=True)
    def est_verifie(self, obj):
        return obj.est_verifie

    @admin.action(description="Valider (publier) les avis sélectionnés")
    def valider_avis(self, request, queryset):
        nb = queryset.update(
            statut_validation=Avis.StatutValidation.VALIDE,
            date_validation=timezone.now(),
        )
        self.message_user(request, f"{nb} avis validé(s).")

    @admin.action(description="Refuser les avis sélectionnés")
    def refuser_avis(self, request, queryset):
        nb = queryset.update(statut_validation=Avis.StatutValidation.REFUSE)
        self.message_user(request, f"{nb} avis refusé(s).")


@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "type_cible", "cible", "created_at")
    list_filter = ("created_at",)
    list_select_related = ("utilisateur", "destination", "site", "circuit", "guide")
    search_fields = ("utilisateur__username", "utilisateur__email")
    autocomplete_fields = ("utilisateur", "destination", "site", "circuit", "guide")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("utilisateur",)}),
        ("Objet mis en favori (en renseigner un seul)", {"fields": ("destination", "site", "circuit", "guide")}),
        ("Horodatage", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Type")
    def type_cible(self, obj):
        return obj.type_cible

    @admin.display(description="Cible")
    def cible(self, obj):
        return obj.cible
