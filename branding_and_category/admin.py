from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    MenuItem,
    ContributorPermission,
    PartnerBranding,
    ProviderMasterCategory,
    ClientCategory,
    QuestionCategory
)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — ROLES & PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('item_key', 'label', 'layer', 'module', 'is_active', 'sort_order')
    list_filter = ('layer', 'is_active', 'module')
    search_fields = ('item_key', 'label', 'description', 'module')
    list_editable = ('is_active', 'sort_order', 'label')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Menu Item Details'), {
            'fields': ('layer', 'module', 'item_key', 'label', 'description')
        }),
        (_('Organization'), {
            'fields': ('sort_order', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def __str__(self):
        return f"{self.item_key}"


@admin.register(ContributorPermission)
class ContributorPermissionAdmin(admin.ModelAdmin):
    list_display = ('user_layer', 'menu_item', 'access_level', 'granted_by', 'granted_at')
    list_filter = ('access_level', 'granted_at', 'menu_item__layer')
    search_fields = ('user_layer__user__email', 'menu_item__item_key', 'menu_item__label')
    raw_id_fields = ('user_layer', 'menu_item', 'granted_by')
    readonly_fields = ('granted_at', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Permission Details'), {
            'fields': ('user_layer', 'menu_item', 'access_level')
        }),
        (_('Grant Information'), {
            'fields': ('granted_by', 'granted_at')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'user_layer__user', 'menu_item', 'granted_by'
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — BRANDING & WHITE-LABEL
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(PartnerBranding)
class PartnerBrandingAdmin(admin.ModelAdmin):
    list_display = ('partner', 'logo_preview', 'custom_subdomain', 'dns_verified', 'sender_email')
    list_filter = ('dns_verified',)
    search_fields = ('partner__company_name', 'custom_subdomain', 'sender_email')
    raw_id_fields = ('partner',)
    readonly_fields = ('dns_verified_at', 'created_at', 'updated_at', 'logo_preview')
    
    fieldsets = (
        (_('Partner'), {
            'fields': ('partner',)
        }),
        (_('Visual Branding'), {
            'fields': ('logo_url', 'logo_preview', 'primary_color', 'secondary_color', 'font_family'),
            'classes': ('wide',)
        }),
        (_('Domain & Email'), {
            'fields': ('custom_subdomain', 'sender_email', 'sender_name', 'dns_verified', 'dns_verified_at'),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def logo_preview(self, obj):
        """Display logo preview in admin"""
        if obj.logo_url:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.logo_url
            )
        return "No logo"
    logo_preview.short_description = 'Logo Preview'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('partner')


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — INDUSTRY & CATEGORY MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ProviderMasterCategory)
class ProviderMasterCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'sort_order', 'short_description')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'sort_order')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Category Details'), {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('Organization'), {
            'fields': ('sort_order',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def short_description(self, obj):
        """Truncate long description"""
        if obj.description:
            return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description
        return "-"
    short_description.short_description = 'Description'


@admin.register(ClientCategory)
class ClientCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'assessment', 'master_category', 'weight_percentage', 'is_active', 'sort_order')
    list_filter = ('is_active', 'client', 'assessment')
    search_fields = ('name', 'description', 'client__full_name', 'client__company_name')
    raw_id_fields = ('client', 'assessment', 'master_category')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('sort_order', 'is_active', 'weight_percentage')
    
    fieldsets = (
        (_('Category Details'), {
            'fields': ('client', 'assessment', 'name', 'description')
        }),
        (_('Scoring Configuration'), {
            'fields': ('weight_percentage', 'master_category')
        }),
        (_('Organization'), {
            'fields': ('sort_order', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'client', 'assessment', 'master_category'
        )
    
    def master_category(self, obj):
        """Display master category name"""
        return obj.master_category.name if obj.master_category else "-"
    master_category.short_description = 'Master Category'
    
    actions = ['activate_categories', 'deactivate_categories']
    
    def activate_categories(self, request, queryset):
        """Bulk activate categories"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} category(ies).')
    activate_categories.short_description = 'Activate selected categories'
    
    def deactivate_categories(self, request, queryset):
        """Bulk deactivate categories"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} category(ies).')
    deactivate_categories.short_description = 'Deactivate selected categories'





class QuestionCategoryAdmin(admin.ModelAdmin):
    
    raw_id_fields = ('assessment', 'category', 'question')
    
    list_display = (
        'id',
        'assessment_title',
        'category_name',
        'question_text_short',
        'sort_order',
        'created_at',
    )
    list_filter = ('assessment', 'category', 'assessment__client')
    search_fields = ('assessment__title', 'category__name', 'question__question_text')
    ordering = ('assessment__client', 'assessment', 'category__sort_order', 'sort_order')
    list_per_page = 50
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('assessment', 'category', 'question', 'sort_order'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    @admin.display(description='Assessment', ordering='assessment__title')
    def assessment_title(self, obj):
        return obj.assessment.title if obj.assessment else '-'
    
    @admin.display(description='Category', ordering='category__sort_order')
    def category_name(self, obj):
        return obj.category.name if obj.category else '-'
    
    @admin.display(description='Question')
    def question_text_short(self, obj):
        if obj.question:
            text = obj.question.question_text
            return text[:70] + '...' if len(text) > 70 else text
        return '-'


admin.site.register(QuestionCategory, QuestionCategoryAdmin)