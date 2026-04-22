from django.contrib import admin
from django.utils.html import format_html
from .models import (Report,ReportActionItem,
    ReportAnswerActionItem,
    ReportUniqueActionItem,
    MiniOffer,
    ReportTheme,
    ClientReportSettings,)


@admin.register(Report)
class SimpleReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'client', 'status', 'is_locked', 'generated_at', 'sent_at')
    list_filter = ('status', 'is_locked', 'generated_at')
    search_fields = ('session__guest__email', 'client__full_name')
    raw_id_fields = ('session', 'client', 'sent_by')
    readonly_fields = ('created_at', 'updated_at', 'resend_count')
    
    fieldsets = (
        (None, {
            'fields': ('session', 'client', 'status', 'is_locked')
        }),
        ('PDF & Dates', {
            'fields': ('pdf_url', 'generated_at', 'approved_at', 'sent_at', 'sent_by')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at', 'resend_count'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reports', 'send_reports']
    
    def approve_reports(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'Approved {updated} report(s).')
    approve_reports.short_description = 'Approve selected reports'
    
    def send_reports(self, request, queryset):
        updated = queryset.update(status='sent', is_locked=True)
        self.message_user(request, f'Sent {updated} report(s).')
    send_reports.short_description = 'Send selected reports'





# ═══════════════════════════════════════════════════════════════════════════════
# REPORT ACTION ITEMS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ReportActionItem)
class ReportActionItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_link', 'display_title_short', 'is_included', 'sort_order')
    list_filter = ('is_included', 'created_at')
    search_fields = ('title_snapshot', 'client_edited_title', 'action_item__title')
    raw_id_fields = ('report', 'action_item', 'category')
    readonly_fields = ('title_snapshot', 'description_snapshot', 'created_at', 'updated_at')
    list_editable = ('is_included', 'sort_order')
    
    fieldsets = (
        (None, {
            'fields': ('report', 'action_item', 'category')
        }),
        ('Snapshot (Frozen at generation)', {
            'fields': ('title_snapshot', 'description_snapshot'),
            'classes': ('wide',)
        }),
        ('Client Edits', {
            'fields': ('client_edited_title', 'client_edited_desc'),
            'description': 'Client edits override the snapshot values'
        }),
        ('Settings', {
            'fields': ('is_included', 'sort_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def report_link(self, obj):
        return format_html('<a href="/admin/reports/report/{}/change/">Report #{}</a>', obj.report_id, obj.report_id)
    report_link.short_description = 'Report'
    
    def display_title_short(self, obj):
        title = obj.display_title()
        return title[:60] + '...' if len(title) > 60 else title
    display_title_short.short_description = 'Title'


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT ANSWER ACTION ITEMS (Audit Table)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ReportAnswerActionItem)
class ReportAnswerActionItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_link', 'answer_choice_link', 'action_item_link')
    list_filter = ('report__status',)
    search_fields = ('report__id', 'action_item__title', 'answer_choice__choice_text')
    raw_id_fields = ('report', 'session', 'answer_choice', 'action_item')
    
    def report_link(self, obj):
        return format_html('<a href="/admin/reports/report/{}/change/">Report #{}</a>', obj.report_id, obj.report_id)
    report_link.short_description = 'Report'
    
    def answer_choice_link(self, obj):
        return obj.answer_choice.choice_text[:50] if obj.answer_choice else '-'
    answer_choice_link.short_description = 'Answer Choice'
    
    def action_item_link(self, obj):
        return obj.action_item.title[:50] if obj.action_item else '-'
    action_item_link.short_description = 'Action Item'
    
    def has_add_permission(self, request):
        return False  # Audit table - should be write-only via code
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit table - should not be edited


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT UNIQUE ACTION ITEMS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ReportUniqueActionItem)
class ReportUniqueActionItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_link', 'action_item_link', 'sort_order')
    list_filter = ('report__status',)
    search_fields = ('report__id', 'action_item__title')
    raw_id_fields = ('report', 'action_item')
    list_editable = ('sort_order',)
    
    def report_link(self, obj):
        return format_html('<a href="/admin/reports/report/{}/change/">Report #{}</a>', obj.report_id, obj.report_id)
    report_link.short_description = 'Report'
    
    def action_item_link(self, obj):
        return obj.action_item.title[:60] if obj.action_item else '-'
    action_item_link.short_description = 'Action Item'


# ═══════════════════════════════════════════════════════════════════════════════
# MINI OFFERS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(MiniOffer)
class MiniOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_link', 'headline_short', 'is_ai_generated', 'client_edited')
    list_filter = ('is_ai_generated', 'client_edited', 'created_at')
    search_fields = ('headline', 'body_text', 'report__id')
    raw_id_fields = ('report',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('report',)
        }),
        ('Content', {
            'fields': ('headline', 'body_text')
        }),
        ('Call to Action - Pay', {
            'fields': ('cta_pay_label', 'cta_pay_url')
        }),
        ('Call to Action - Appeal', {
            'fields': ('cta_appeal_label', 'cta_appeal_url')
        }),
        ('AI Information', {
            'fields': ('is_ai_generated', 'client_edited')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def report_link(self, obj):
        return format_html('<a href="/admin/reports/report/{}/change/">Report #{}</a>', obj.report_id, obj.report_id)
    report_link.short_description = 'Report'
    
    def headline_short(self, obj):
        return obj.headline[:60] + '...' if len(obj.headline) > 60 else obj.headline
    headline_short.short_description = 'Headline'


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT THEMES
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ReportTheme)
class ReportThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'preview_link', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active', 'sort_order')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active', 'sort_order')
        }),
        ('Preview', {
            'fields': ('preview_url', 'preview_link'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def preview_link(self, obj):
        if obj.preview_url:
            return format_html('<a href="{}" target="_blank">🔍 View Preview</a>', obj.preview_url)
        return "No preview"
    preview_link.short_description = 'Preview'
    
    actions = ['activate_themes', 'deactivate_themes']
    
    def activate_themes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} theme(s).')
    activate_themes.short_description = 'Activate selected themes'
    
    def deactivate_themes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} theme(s).')
    deactivate_themes.short_description = 'Deactivate selected themes'


# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT REPORT SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ClientReportSettings)
class ClientReportSettingsAdmin(admin.ModelAdmin):
    list_display = ('client_link', 'theme', 'score_chart_type', 'has_logo', 'primary_color_preview')
    list_filter = ('theme', 'score_chart_type')
    search_fields = ('client__full_name', 'client__company_name')
    raw_id_fields = ('client', 'theme')
    readonly_fields = ('created_at', 'updated_at', 'color_preview')
    
    fieldsets = (
        (None, {
            'fields': ('client',)
        }),
        ('Theme', {
            'fields': ('theme',)
        }),
        ('Branding', {
            'fields': ('logo_url', 'primary_color', 'secondary_color', 'color_preview')
        }),
        ('Typography', {
            'fields': ('heading_font', 'body_font')
        }),
        ('Chart Settings', {
            'fields': ('score_chart_type',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def client_link(self, obj):
        return format_html(
            '<a href="/admin/users/client/{}/change/">{}</a>',
            obj.client_id,
            obj.client.full_name or obj.client.company_name
        )
    client_link.short_description = 'Client'
    
    def has_logo(self, obj):
        return '✓' if obj.logo_url else '✗'
    has_logo.short_description = 'Has Logo'
    
    def primary_color_preview(self, obj):
        if obj.primary_color:
            return format_html(
                '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px; color: white;">{}</span>',
                obj.primary_color,
                obj.primary_color
            )
        return "No color set"
    primary_color_preview.short_description = 'Color Preview'
    
    def color_preview(self, obj):
        return format_html(
            '<div style="display: flex; gap: 10px;">'
            '<div><strong>Primary:</strong><br>'
            '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px; color: white;">{}</span></div>'
            '<div><strong>Secondary:</strong><br>'
            '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px; color: white;">{}</span></div>'
            '</div>',
            obj.primary_color or '#cccccc',
            obj.primary_color or 'Not set',
            obj.secondary_color or '#cccccc',
            obj.secondary_color or 'Not set'
        )
    color_preview.short_description = 'Color Preview'

