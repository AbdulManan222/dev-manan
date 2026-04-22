from django.contrib import admin
from django.utils.html import format_html
from .models import AIPromptTemplate, AIGenerationLog


# ═══════════════════════════════════════════════════════════════════════════════
# AI PROMPT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(AIPromptTemplate)
class AIPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('use_case', 'version', 'model', 'is_active', 'updated_at')
    list_filter = ('use_case', 'is_active', 'model')
    search_fields = ('use_case', 'prompt_text', 'notes')
    readonly_fields = ('version', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    
    fieldsets = (
        (None, {
            'fields': ('use_case', 'prompt_text', 'model', 'is_active')
        }),
        ('Version Info', {
            'fields': ('version',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_templates', 'deactivate_templates']
    
    def activate_templates(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Activated {updated} template(s).')
    activate_templates.short_description = 'Activate selected templates'
    
    def deactivate_templates(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {updated} template(s).')
    deactivate_templates.short_description = 'Deactivate selected templates'


# ═══════════════════════════════════════════════════════════════════════════════
# AI GENERATION LOGS (Read-only)
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(AIGenerationLog)
class AIGenerationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'use_case', 'client_action', 'tokens_used', 'generated_at')
    list_filter = ('use_case', 'client_action', 'generated_at')
    search_fields = ('use_case', 'raw_response', 'client__full_name', 'session__guest__email')
    raw_id_fields = ('prompt_template', 'client', 'session', 'report')
    readonly_fields = ('generated_at', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('prompt_template', 'use_case', 'model_used')
        }),
        ('Related Objects', {
            'fields': ('client', 'session', 'report')
        }),
        ('AI Data', {
            'fields': ('context_payload', 'raw_response', 'parsed_output')
        }),
        ('Feedback', {
            'fields': ('client_action', 'tokens_used')
        }),
        ('Timestamps', {
            'fields': ('generated_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Make logs read-only
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow superusers to change client_action if needed
        if request.user.is_superuser and obj:
            return True
        return False
    
    actions = ['mark_as_accepted', 'mark_as_edited', 'mark_as_rejected']
    
    def mark_as_accepted(self, request, queryset):
        updated = queryset.update(client_action='accepted')
        self.message_user(request, f'Marked {updated} log(s) as accepted.')
    mark_as_accepted.short_description = 'Mark as Accepted'
    
    def mark_as_edited(self, request, queryset):
        updated = queryset.update(client_action='edited')
        self.message_user(request, f'Marked {updated} log(s) as edited.')
    mark_as_edited.short_description = 'Mark as Edited'
    
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(client_action='rejected')
        self.message_user(request, f'Marked {updated} log(s) as rejected.')
    mark_as_rejected.short_description = 'Mark as Rejected'