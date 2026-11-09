from django.contrib import admin
from django.utils import timezone

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "nom_visiteur",
        "circuit",
        "guide",
        "date_depart",
        "nombre_personnes",
        "montant_total",
        "statut",
        "created_at",
    )
    list_display_links = ("reference", "nom_visiteur")
    list_filter = ("statut", "date_depart", "circuit__destination_depart__region__pays", "created_at")
    list_select_related = ("circuit", "guide", "utilisateur", "pays_visiteur")
    search_fields = (
        "reference",
        "nom_visiteur",
        "email_visiteur",
        "telephone_visiteur",
        "circuit__titre",
        "guide__nom_complet",
    )
    autocomplete_fields = ("utilisateur", "pays_visiteur", "circuit", "guide")
    readonly_fields = ("reference", "montant_total", "date_reponse", "created_at", "updated_at")
    date_hierarchy = "date_depart"
    actions = ["accepter_reservations", "refuser_reservations", "marquer_terminees"]
    fieldsets = (
        ("Référence & statut", {"fields": (("reference", "statut", "date_reponse"),)}),
        (
            "Visiteur",
            {
                "fields": (
                    "utilisateur",
                    ("nom_visiteur", "pays_visiteur"),
                    ("email_visiteur", "telephone_visiteur"),
                )
            },
        ),
        (
            "Prestation réservée",
            {
                "fields": (
                    ("circuit", "guide"),
                    ("date_depart", "date_fin", "nombre_personnes"),
                    ("prix_unitaire", "montant_total"),
                )
            },
        ),
        ("Demandes & suivi", {"fields": ("demandes_speciales", "motif_refus_ou_annulation")}),
        ("Horodatage", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.action(description="Accepter les réservations sélectionnées")
    def accepter_reservations(self, request, queryset):
        nb = queryset.update(statut=Reservation.Statut.ACCEPTEE, date_reponse=timezone.now())
        self.message_user(request, f"{nb} réservation(s) acceptée(s).")

    @admin.action(description="Refuser les réservations sélectionnées")
    def refuser_reservations(self, request, queryset):
        nb = queryset.update(statut=Reservation.Statut.REFUSEE, date_reponse=timezone.now())
        self.message_user(request, f"{nb} réservation(s) refusée(s).")

    @admin.action(description="Marquer comme terminées")
    def marquer_terminees(self, request, queryset):
        nb = queryset.update(statut=Reservation.Statut.TERMINEE)
        self.message_user(request, f"{nb} réservation(s) marquée(s) comme terminée(s).")
