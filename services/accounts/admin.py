from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "created_at")
    search_fields = ("name", "domain")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "org", "is_staff", "is_active")
    list_filter = ("org", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Organization", {"fields": ("org",)}),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {"fields": ("org",)}),
    )
