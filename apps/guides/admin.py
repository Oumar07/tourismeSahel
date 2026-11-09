from django.contrib import admin
from django.utils import timezone

from apps.core.admin_utils import image_thumbnail

from .models import DisponibiliteGuide, Guide, Langue, SpecialiteGuide


@admin.register(Langue)
class LangueAdmin(admin.ModelAdmin):
    list_display = ("nom", "code")
    search_fields = ("nom", "code")


@admin.register(SpecialiteGuide)
class SpecialiteGuideAdmin(admin.ModelAdmin):
    list_display = ("nom", "icone")
    search_fields = ("nom",)
    prepopulated_fields = {"slug": ("nom",)}


class DisponibiliteGuideInline(admin.TabularInline):
    model = DisponibiliteGuide
    fields = ("date_debut", "date_fin", "statut", "note")
    extra = 1


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = (
        "apercu_liste",
        "nom_complet",
        "utilisateur",
        "annees_experience",
        "tarif_journalier",
        "statut_verification",
        "en_vedette",
        "est_actif",
    )
    list_display_links = ("apercu_liste", "nom_complet")
    list_editable = ("en_vedette", "est_actif")
    list_filter = ("statut_verification", "specialites", "langues", "regions__pays", "en_vedette", "est_actif")
    list_select_related = ("utilisateur",)
    search_fields = ("nom_complet", "titre_professionnel", "numero_licence", "utilisateur__email")
    autocomplete_fields = ("utilisateur",)
    filter_horizontal = ("langues", "specialites", "regions")
    prepopulated_fields = {"slug": ("nom_complet",)}
    readonly_fields = ("apercu_photo", "date_verification", "created_at", "updated_at")
    inlines = [DisponibiliteGuideInline]
    actions = ["marquer_verifies", "marquer_refuses"]
    fieldsets = (
        (None, {"fields": ("utilisateur", "nom_complet", "slug", "titre_professionnel")}),
        ("Présentation & photo", {"fields": ("bio", ("photo", "apercu_photo"))}),
        ("Compétences & zones", {"fields": ("langues", "specialites", "regions")}),
        ("Expérience & tarif", {"fields": (("annees_experience", "tarif_journalier"),)}),
        (
            "Vérification professionnelle",
            {
                "fields": (
                    "numero_licence",
                    "document_justificatif",
                    ("statut_verification", "date_verification"),
                    "commentaire_moderation",
                )
            },
        ),
        ("Publication", {"fields": ("en_vedette", "est_actif")}),
        ("Suivi", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Photo")
    def apercu_liste(self, obj):
        return image_thumbnail(obj.photo, height=40)

    @admin.display(description="Aperçu")
    def apercu_photo(self, obj):
        return image_thumbnail(obj.photo, height=140)

    @admin.action(description="Valider les guides sélectionnés (Vérifié)")
    def marquer_verifies(self, request, queryset):
        nb = queryset.update(
            statut_verification=Guide.StatutVerification.VERIFIE,
            date_verification=timezone.now(),
        )
        self.message_user(request, f"{nb} guide(s) marqué(s) comme vérifié(s).")

    @admin.action(description="Refuser les guides sélectionnés")
    def marquer_refuses(self, request, queryset):
        nb = queryset.update(statut_verification=Guide.StatutVerification.REFUSE)
        self.message_user(request, f"{nb} guide(s) marqué(s) comme refusé(s).")


@admin.register(DisponibiliteGuide)
class DisponibiliteGuideAdmin(admin.ModelAdmin):
    list_display = ("guide", "date_debut", "date_fin", "statut", "note")
    list_filter = ("statut", "date_debut")
    list_select_related = ("guide",)
    search_fields = ("guide__nom_complet", "note")
    autocomplete_fields = ("guide",)
    date_hierarchy = "date_debut"
