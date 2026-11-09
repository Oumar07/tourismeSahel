from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.core.admin_utils import image_thumbnail

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("apercu_avatar", "username", "email", "first_name", "last_name", "role", "pays_origine", "is_active")
    list_display_links = ("apercu_avatar", "username")
    list_filter = ("role", "is_staff", "is_active", "pays_origine")
    list_select_related = ("pays_origine",)
    search_fields = ("username", "email", "first_name", "last_name", "telephone")
    autocomplete_fields = ("pays_origine",)
    readonly_fields = ("apercu_avatar", "last_login", "date_joined", "created_at", "updated_at")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profil TourismeSahel", {"fields": ("role", "telephone", "pays_origine", ("avatar", "apercu_avatar"))}),
        ("Suivi", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Profil TourismeSahel", {"fields": ("email", "first_name", "last_name", "role", "telephone", "pays_origine")}),
    )

    @admin.display(description="Photo")
    def apercu_avatar(self, obj):
        return image_thumbnail(obj.avatar, height=36)
