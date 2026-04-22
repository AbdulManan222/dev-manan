from django.contrib import admin

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    NotificationEventType,
    NotificationTemplate,
    NotificationLog,
    SubscriptionPlan,
    PartnerSubscription,
    BillingEvent,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 14 — NOTIFICATIONS & EMAILS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(NotificationEventType)
class NotificationEventTypeAdmin(admin.ModelAdmin):
    list_display = ('event_key', 'label', 'recipient', 'is_active')
    list_filter = ('recipient', 'is_active')
    search_fields = ('event_key', 'label', 'description')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('event_key', 'label', 'description', 'recipient', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'partner_scope', 'subject_preview', 'is_active')
    list_filter = ('event_type', 'partner', 'is_active')
    search_fields = ('subject', 'body_html', 'event_type__event_key')
    raw_id_fields = ('event_type', 'partner')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
    
    fieldsets = (
        (None, {
            'fields': ('event_type', 'partner', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'body_html', 'body_text'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def partner_scope(self, obj):
        if obj.partner:
            return obj.partner.company_name
        return '🏢 Provider Default'
    partner_scope.short_description = 'Scope'
    
    def subject_preview(self, obj):
        return obj.subject[:60] + '...' if len(obj.subject) > 60 else obj.subject
    subject_preview.short_description = 'Subject'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type', 'recipient_email', 'status_badge', 'sent_at')
    list_filter = ('status', 'event_type', 'sent_at')
    search_fields = ('recipient_email', 'error_message', 'sendgrid_msg_id')
    raw_id_fields = ('event_type', 'template', 'session', 'report')
    readonly_fields = ('sent_at', 'created_at', 'updated_at')
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        (None, {
            'fields': ('event_type', 'template', 'recipient_email')
        }),
        ('Related Objects', {
            'fields': ('session', 'report')
        }),
        ('Status', {
            'fields': ('status', 'sendgrid_msg_id', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'sent': '#28a745',
            'failed': '#dc3545',
            'bounced': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Logs should be append-only
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be edited


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 15 — BILLING & SUBSCRIPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'price_annual', 'max_clients', 'max_assessments', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'features')
    list_editable = ('price_monthly', 'price_annual', 'max_clients', 'max_assessments', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_annual')
        }),
        ('Limits', {
            'fields': ('max_clients', 'max_assessments')
        }),
        ('Features', {
            'fields': ('features',),
            'classes': ('wide',),
            'help_text': 'JSON format: {"feature1": true, "feature2": false}'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_plans', 'deactivate_plans']
    
    def activate_plans(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} plan(s).')
    activate_plans.short_description = 'Activate selected plans'
    
    def deactivate_plans(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} plan(s).')
    deactivate_plans.short_description = 'Deactivate selected plans'


@admin.register(PartnerSubscription)
class PartnerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('partner_link', 'plan', 'status_badge', 'billing_cycle', 'current_period_end', 'is_expiring_soon')
    list_filter = ('status', 'billing_cycle', 'plan')
    search_fields = ('partner__company_name', 'stripe_customer_id', 'stripe_sub_id')
    raw_id_fields = ('partner', 'plan')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'current_period_end'
    
    fieldsets = (
        (None, {
            'fields': ('partner', 'plan', 'status', 'billing_cycle')
        }),
        ('Billing Period', {
            'fields': ('current_period_start', 'current_period_end')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_customer_id', 'stripe_sub_id', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def partner_link(self, obj):
        return format_html(
            '<a href="/admin/users/partner/{}/change/">{}</a>',
            obj.partner_id,
            obj.partner.company_name
        )
    partner_link.short_description = 'Partner'
    
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'past_due': '#dc3545',
            'cancelled': '#6c757d',
            'trialing': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def is_expiring_soon(self, obj):
        if obj.current_period_end:
            days_left = (obj.current_period_end - timezone.now().date()).days
            if 0 <= days_left <= 7:
                return format_html('<span style="color: orange;">⚠️ {} days left</span>', days_left)
            if days_left < 0:
                return format_html('<span style="color: red;">Expired</span>')
        return '-'
    is_expiring_soon.short_description = 'Expiring Soon'
    
    actions = ['activate_subscriptions', 'cancel_subscriptions', 'mark_past_due']
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'Activated {updated} subscription(s).')
    activate_subscriptions.short_description = 'Set as Active'
    
    def cancel_subscriptions(self, request, queryset):
        updated = queryset.update(status='cancelled', cancelled_at=timezone.now())
        self.message_user(request, f'Cancelled {updated} subscription(s).')
    cancel_subscriptions.short_description = 'Cancel subscriptions'
    
    def mark_past_due(self, request, queryset):
        updated = queryset.update(status='past_due')
        self.message_user(request, f'Marked {updated} subscription(s) as Past Due.')
    mark_past_due.short_description = 'Mark as Past Due'


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'partner_link', 'event_type', 'client_link', 'occurred_at', 'invoice_id')
    list_filter = ('event_type', 'occurred_at')
    search_fields = ('partner__company_name', 'client__full_name', 'invoice_id')
    raw_id_fields = ('partner', 'client', 'session')
    readonly_fields = ('occurred_at', 'created_at', 'updated_at')
    date_hierarchy = 'occurred_at'
    
    fieldsets = (
        (None, {
            'fields': ('partner', 'client', 'session', 'event_type')
        }),
        ('Billing Info', {
            'fields': ('occurred_at', 'invoice_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def partner_link(self, obj):
        return format_html(
            '<a href="/admin/users/partner/{}/change/">{}</a>',
            obj.partner_id,
            obj.partner.slug
        )
    partner_link.short_description = 'Partner'
    
    def client_link(self, obj):
        if obj.client:
            return format_html(
                '<a href="/admin/users/client/{}/change/">{}</a>',
                obj.client_id,
                obj.client.full_name or obj.client.company_name
            )
        return '-'
    client_link.short_description = 'Client'
    
    def has_change_permission(self, request, obj=None):
        return False  # Billing events should be append-only

