from django.utils import timezone
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Avg
from .models import (
    Assessment,
    ScoringThreshold,
    Question,
    AnswerChoice,
    QuestionAnswer,
    ActionItem,
    AnswerActionItemMapping,
    AssessmentSession,
    GuestResponse,
    AssessmentResponseScore,
    SessionCategoryScore,
    SessionOverallScore,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — ASSESSMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class ScoringThresholdInline(admin.TabularInline):
    """Inline for scoring thresholds within assessment"""
    model = ScoringThreshold
    extra = 1
    fields = ['category', 'label', 'min_score', 'max_score']
    show_change_link = True


class QuestionInline(admin.TabularInline):
    """Inline for questions within assessment"""
    model = Question
    extra = 0
    fields = ['question_text', 'category', 'sort_order', 'is_required', 'is_active']
    show_change_link = True
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'is_active', 'question_count', 'activated_at', 'created_at')
    list_filter = ('status', 'is_active', 'created_at', 'client')
    search_fields = ('title', 'client__full_name', 'client__company_name', 'industry')
    raw_id_fields = ('client', 'cloned_from')
    readonly_fields = ('activated_at', 'archived_at', 'created_at', 'updated_at', 'clone_link')
    inlines = [ScoringThresholdInline, QuestionInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('client', 'title', 'industry', 'status', 'is_active')
        }),
        (_('Cloning'), {
            'fields': ('cloned_from', 'clone_link'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('activated_at', 'archived_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_count(self, obj):
        """Display number of questions"""
        count = obj.questions.filter(is_active=True).count()
        url = reverse('admin:assessment_question_changelist') + f'?assessment__id__exact={obj.id}'
        return format_html('<a href="{}">{} questions</a>', url, count)
    question_count.short_description = 'Questions'
    
    def clone_link(self, obj):
        """Link to clone this assessment"""
        if obj.pk:
            return format_html(
                '<a href="{}?clone_from={}" class="button">Clone Assessment</a>',
                reverse('admin:assessment_assessment_add'),
                obj.pk
            )
        return "Save to enable cloning"
    clone_link.short_description = 'Clone Action'
    
    actions = ['clone_selected_assessments']
    
    def clone_selected_assessments(self, request, queryset):
        """Bulk clone action"""
        cloned_count = 0
        for assessment in queryset:
            assessment.clone()
            cloned_count += 1
        self.message_user(request, f'Successfully cloned {cloned_count} assessment(s).')
    clone_selected_assessments.short_description = 'Clone selected assessments'


@admin.register(ScoringThreshold)
class ScoringThresholdAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'category', 'label', 'min_score', 'max_score')
    list_filter = ('label', 'assessment')
    search_fields = ('assessment__title', 'category__name')
    raw_id_fields = ('assessment', 'category')
    readonly_fields = ('created_at', 'updated_at')


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — QUESTIONS & ANSWER CHOICES
# ═══════════════════════════════════════════════════════════════════════════════

class AnswerChoiceInline(admin.TabularInline):
    """Inline for answer choices within question"""
    model = AnswerChoice
    extra = 1
    fields = ['choice_text', 'point_value', 'sort_order', 'is_active']
    show_change_link = True


class QuestionAnswerInline(admin.TabularInline):
    """Inline for question-answer mapping"""
    model = QuestionAnswer
    extra = 1
    fields = ['answer_choice', 'is_correct']
    raw_id_fields = ['answer_choice']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'assessment', 'category', 'sort_order', 'is_required', 'is_active', 'answer_count')
    list_filter = ('is_required', 'is_active', 'category', 'assessment')
    search_fields = ('question_text', 'assessment__title', 'category__name')
    raw_id_fields = ('assessment', 'category')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AnswerChoiceInline, QuestionAnswerInline]
    list_editable = ['sort_order', 'is_required', 'is_active']
    
    fieldsets = (
        (_('Question Details'), {
            'fields': ('assessment', 'category', 'question_text', 'is_required')
        }),
        (_('Organization'), {
            'fields': ('sort_order', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def short_text(self, obj):
        """Truncate long question text"""
        return obj.question_text[:80] + '...' if len(obj.question_text) > 80 else obj.question_text
    short_text.short_description = 'Question'
    
    def answer_count(self, obj):
        """Display number of answer choices"""
        count = obj.answer_choices.filter(is_active=True).count()
        url = reverse('admin:assessment_answerchoice_changelist') + f'?question__id__exact={obj.id}'
        return format_html('<a href="{}">{} answers</a>', url, count)
    answer_count.short_description = 'Answers'


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'question', 'point_value', 'sort_order', 'is_active')
    list_filter = ('is_active', 'question__assessment')
    search_fields = ('choice_text', 'question__question_text')
    raw_id_fields = ('question',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ['point_value', 'sort_order', 'is_active']
    
    fieldsets = (
        (_('Answer Details'), {
            'fields': ('question', 'choice_text', 'point_value')
        }),
        (_('Organization'), {
            'fields': ('sort_order', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def short_text(self, obj):
        """Truncate long choice text"""
        return obj.choice_text[:60] + '...' if len(obj.choice_text) > 60 else obj.choice_text
    short_text.short_description = 'Answer Choice'


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer_choice', 'is_correct')
    list_filter = ('is_correct', 'question__assessment')
    search_fields = ('question__question_text', 'answer_choice__choice_text')
    raw_id_fields = ('question', 'answer_choice')


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — ACTION ITEMS & MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'category', 'is_ai_generated', 'is_active', 'sort_order')
    list_filter = ('is_ai_generated', 'is_active', 'client', 'category')
    search_fields = ('title', 'description', 'client__full_name', 'category__name')
    raw_id_fields = ('client', 'category', 'ai_suggestion')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ['sort_order', 'is_active']
    
    fieldsets = (
        (_('Action Item Details'), {
            'fields': ('client', 'category', 'title', 'description')
        }),
        (_('AI Information'), {
            'fields': ('is_ai_generated', 'ai_suggestion'),
            'classes': ('collapse',)
        }),
        (_('Organization'), {
            'fields': ('sort_order', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AnswerActionItemMapping)
class AnswerActionItemMappingAdmin(admin.ModelAdmin):
    list_display = ('answer_choice', 'action_item', 'created_at')
    list_filter = ('answer_choice__question__assessment',)
    search_fields = ('answer_choice__choice_text', 'action_item__title')
    raw_id_fields = ('answer_choice', 'action_item')
    readonly_fields = ('created_at',)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 9 — GUEST SESSIONS & RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════

class GuestResponseInline(admin.TabularInline):
    """Inline for responses within session"""
    model = GuestResponse
    extra = 0
    fields = ['question', 'answer_choice', 'points_awarded', 'answered_at']
    readonly_fields = ['answered_at', 'points_awarded']
    raw_id_fields = ['question', 'answer_choice']
    show_change_link = True
    can_delete = False
    max_num = 0  # Don't allow adding via inline


class SessionCategoryScoreInline(admin.TabularInline):
    """Inline for category scores within session"""
    model = SessionCategoryScore
    extra = 0
    fields = ['category', 'percentage', 'label', 'calculated_at']
    readonly_fields = ['category', 'raw_score', 'max_possible', 'percentage', 'label', 'calculated_at']
    can_delete = False
    max_num = 0


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest', 'assessment', 'client', 'status', 'completion_status', 'expires_at')
    list_filter = ('status', 'created_at', 'assessment', 'client')
    search_fields = ('guest__email', 'guest__first_name', 'guest__last_name', 'assessment__title')
    raw_id_fields = ('guest', 'assessment', 'client')
    readonly_fields = ('started_at', 'last_activity_at', 'completed_at', 'expires_at', 'created_at', 'updated_at', 'session_link')
    inlines = [GuestResponseInline, SessionCategoryScoreInline]
    
    fieldsets = (
        (_('Session Information'), {
            'fields': ('guest', 'assessment', 'client', 'status')
        }),
        (_('Timing'), {
            'fields': ('started_at', 'last_activity_at', 'completed_at', 'expires_at')
        }),
        (_('Additional'), {
            'fields': ('password_created', 'session_link'),
            'classes': ('collapse',)
        }),
        (_('System Fields'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def completion_status(self, obj):
        """Show if session is complete and overall score"""
        if obj.status == 'completed':
            try:
                score = obj.overall_score
                return format_html('<strong>✓ Complete</strong><br>{}%', score.percentage)
            except:
                return '✓ Complete (scoring pending)'
        return obj.status.capitalize()
    completion_status.short_description = 'Status/Score'
    
    def session_link(self, obj):
        """Link to view session results"""
        if obj.pk:
            return format_html(
                '<a href="/admin/assessment/sessionoverallscore/{}/change/" target="_blank">View Overall Score</a>',
                obj.overall_score.pk if hasattr(obj, 'overall_score') else 0
            )
        return "-"
    session_link.short_description = 'Results'
    
    actions = ['mark_as_completed', 'expire_sessions']
    
    def mark_as_completed(self, request, queryset):
        """Bulk mark sessions as completed"""
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'Marked {updated} session(s) as completed.')
    mark_as_completed.short_description = 'Mark as completed'
    
    def expire_sessions(self, request, queryset):
        """Bulk expire sessions"""
        updated = queryset.update(status='expired')
        self.message_user(request, f'Expired {updated} session(s).')
    expire_sessions.short_description = 'Expire selected sessions'


@admin.register(GuestResponse)
class GuestResponseAdmin(admin.ModelAdmin):
    list_display = ('session', 'question', 'answer_choice', 'points_awarded', 'answered_at')
    list_filter = ('session__assessment', 'session__status')
    search_fields = ('session__guest__email', 'question__question_text')
    raw_id_fields = ('session', 'question', 'answer_choice')
    readonly_fields = ('points_awarded', 'answered_at', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """Prevent manual addition of responses"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of responses"""
        return False


@admin.register(AssessmentResponseScore)
class AssessmentResponseScoreAdmin(admin.ModelAdmin):
    list_display = ('response', 'points_awarded')
    raw_id_fields = ('response',)
    readonly_fields = ('points_awarded',)
    
    def has_add_permission(self, request):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 10 — SCORING RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(SessionCategoryScore)
class SessionCategoryScoreAdmin(admin.ModelAdmin):
    list_display = ('session', 'category', 'percentage', 'label', 'calculated_at')
    list_filter = ('label', 'category')
    search_fields = ('session__guest__email', 'category__name')
    raw_id_fields = ('session', 'category')
    readonly_fields = ('raw_score', 'max_possible', 'percentage', 'label', 'calculated_at', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Score Details'), {
            'fields': ('session', 'category', 'raw_score', 'max_possible', 'percentage', 'label')
        }),
        (_('Timestamps'), {
            'fields': ('calculated_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual addition of scores"""
        return False


@admin.register(SessionOverallScore)
class SessionOverallScoreAdmin(admin.ModelAdmin):
    list_display = ('session', 'percentage', 'label', 'calculated_at')
    list_filter = ('label',)
    search_fields = ('session__guest__email',)
    raw_id_fields = ('session',)
    readonly_fields = ('raw_score', 'max_possible', 'percentage', 'label', 'calculated_at', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Overall Score'), {
            'fields': ('session', 'raw_score', 'max_possible', 'percentage', 'label')
        }),
        (_('Timestamps'), {
            'fields': ('calculated_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual addition of scores"""
        return False