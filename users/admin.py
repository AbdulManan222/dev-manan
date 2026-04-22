from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    User,
    UserLayerMembership,
    Provider,
    Partner,
    Client,
    PartnerClient,
    Guest,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — USERS & IDENTITY
# ═══════════════════════════════════════════════════════════════════════════════

class CustomUserAdmin(UserAdmin):
    """Custom admin for User model with email authentication"""
    
    # Fields to display in list view
    list_display = ('email', 'is_active', 'is_staff', 'email_verified', 'created_at')
    list_filter = ('is_active', 'is_staff', 'email_verified', 'created_at')
    search_fields = ('email',)
    ordering = ('email',)
    
    # Fields to show in detail/edit form
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'email_verified', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login_at', 'created_at', 'updated_at')}),
    )
    
    # Fields for creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


class UserLayerMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'layer', 'entity_id', 'role_type', 'is_active')
    list_filter = ('layer', 'role_type', 'is_active')
    search_fields = ('user__email', 'entity_id')
    raw_id_fields = ('user', 'invited_by')
    readonly_fields = ('created_at', 'updated_at')


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — PLATFORM LAYERS
# ═══════════════════════════════════════════════════════════════════════════════

class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'domain')
    readonly_fields = ('created_at', 'updated_at')


class PartnerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'provider', 'slug', 'status', 'license_end')
    list_filter = ('status', 'provider')
    search_fields = ('company_name', 'slug')
    prepopulated_fields = {'slug': ('company_name',)}
    raw_id_fields = ('approved_by',)
    readonly_fields = ('created_at', 'updated_at', 'approved_at')


class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company_name', 'industry', 'status', 'created_at')
    list_filter = ('status', 'industry')
    search_fields = ('full_name', 'company_name', 'email')
    readonly_fields = ('created_at', 'updated_at')


class PartnerClientAdmin(admin.ModelAdmin):
    list_display = ('partner', 'client', 'status', 'added_at')
    list_filter = ('status',)
    search_fields = ('partner__company_name', 'client__full_name')
    readonly_fields = ('added_at', 'created_at', 'updated_at', 'deactivated_at')


class GuestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'company_name', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'company_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTER ALL MODELS
# ═══════════════════════════════════════════════════════════════════════════════

admin.site.register(User, CustomUserAdmin)
admin.site.register(UserLayerMembership, UserLayerMembershipAdmin)
admin.site.register(Provider, ProviderAdmin)
admin.site.register(Partner, PartnerAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(PartnerClient, PartnerClientAdmin)
admin.site.register(Guest, GuestAdmin)