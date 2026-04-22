from django.db import models
from users.models import Client,Guest
from branding_and_category.models import ClientCategory
from ai_engine.models import AIGenerationLog
from django.utils import timezone
# Create your models here.

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — ASSESSMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class Assessment(models.Model):
    """
    One row per assessment a client creates.
    Only one assessment per client can have is_active=True at a time —
    enforced by a PostgreSQL partial unique index (see migration).

    Schema doc: GROUP 6 — assessments table
    """

    STATUS_CHOICES = [
        ("draft",    "Draft"),
        ("active",   "Active"),
        ("archived", "Archived"),
    ]

    client       = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="assessments")
    title        = models.CharField(max_length=255)
    industry     = models.CharField(max_length=255, blank=True)   # snapshot of client.industry
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_active    = models.BooleanField(default=False)
    cloned_from  = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="clones",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    archived_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessments"
        indexes  = [models.Index(fields=["client", "is_active"])]
        # Partial unique index added via RunSQL in migration:
        # CREATE UNIQUE INDEX one_active_per_client
        #   ON assessments (client_id) WHERE is_active = TRUE;

    def __str__(self):
        return f"{self.title} ({'active' if self.is_active else self.status})"

    def clone(self):
        """
        Deep-copy this assessment: creates new Assessment + ClientCategories +
        Questions + AnswerChoices + ScoringThresholds.
        Does NOT copy sessions, responses, or reports.
        """
        from django.db import transaction

        with transaction.atomic():
            new = Assessment.objects.create(
                client=self.client,
                title=f"Copy of {self.title}",
                industry=self.industry,
                status="draft",
                is_active=False,
                cloned_from=self,
            )

            category_map = {}
            for cat in self.categories.filter(is_active=True):
                old_id = cat.pk
                cat.pk = None
                cat.assessment = new
                cat.save()
                category_map[old_id] = cat

            for q in Question.objects.filter(assessment=self, is_active=True):
                old_q_id = q.pk
                choices  = list(q.answer_choices.filter(is_active=True))
                q.pk = None
                q.assessment = new
                q.category   = category_map.get(q.category_id, q.category)
                q.save()
                for ch in choices:
                    ch.pk       = None
                    ch.question = q
                    ch.save()

            for t in self.scoring_thresholds.all():
                t.pk         = None
                t.assessment = new
                t.category   = category_map.get(t.category_id) if t.category_id else None
                t.save()

        return new


class ScoringThreshold(models.Model):
    """
    Score ranges that map to performance labels (Critical / Mediocre / Exceptional).
    category=None means this is the overall assessment threshold.

    Schema doc: GROUP 6 — scoring_thresholds table
    """

    LABEL_CHOICES = [
        ("critical",    "Critical"),
        ("mediocre",    "Mediocre"),
        ("exceptional", "Exceptional"),
    ]

    assessment  = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="scoring_thresholds")
    category    = models.ForeignKey(
        ClientCategory,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="scoring_thresholds",
        help_text="NULL = overall assessment threshold",
    )
    label       = models.CharField(max_length=50, choices=LABEL_CHOICES)
    min_score   = models.DecimalField(max_digits=6, decimal_places=2)
    max_score   = models.DecimalField(max_digits=6, decimal_places=2)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_thresholds"
        indexes  = [models.Index(fields=["assessment", "category"])]

    def __str__(self):
        scope = self.category.name if self.category else "Overall"
        return f"{scope}: {self.label} ({self.min_score}–{self.max_score})"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — QUESTIONS & ANSWER CHOICES
# ═══════════════════════════════════════════════════════════════════════════════

class Question(models.Model):
    """
    Each question belongs to exactly one category and one assessment.
    Multiple choice only. is_active = soft delete.

    Schema doc: GROUP 7 — questions table
    """

    assessment    = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    category      = models.ForeignKey(ClientCategory, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    is_required   = models.BooleanField(default=True)
    sort_order    = models.IntegerField(default=0)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "questions"
        indexes  = [
            models.Index(fields=["assessment", "category"]),
            models.Index(fields=["assessment", "is_active", "sort_order"]),
        ]
        ordering = ["sort_order"]

    def __str__(self):
        return self.question_text[:80]


class AnswerChoice(models.Model):
    """
    One selectable option for a question.
    point_value drives the scoring system.

    Schema doc: GROUP 7 — answer_choices table
    """

    question    = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answer_choices")
    choice_text = models.CharField(max_length=500)
    point_value = models.DecimalField(max_digits=6, decimal_places=2)
    sort_order  = models.IntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "answer_choices"
        indexes  = [models.Index(fields=["question", "is_active"])]
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.choice_text} ({self.point_value} pts)"


class QuestionAnswer(models.Model):
    """
    Explicit mapping of valid answer choices for a question.
    Links Q&A structure for report display and quiz-mode support.

    Schema doc: GROUP 7 — questions_answers table
    """

    question      = models.ForeignKey(Question,     on_delete=models.CASCADE, related_name="question_answers")
    answer_choice = models.ForeignKey(AnswerChoice, on_delete=models.CASCADE, related_name="question_answers")
    is_correct    = models.BooleanField(null=True, blank=True)   # null = scoring-only mode

    class Meta:
        db_table        = "questions_answers"
        unique_together = [("question", "answer_choice")]

    def __str__(self):
        return f"Q#{self.question_id} ↔ A#{self.answer_choice_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — ACTION ITEMS & MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

class ActionItem(models.Model):
    client = models.ForeignKey(
        'users.Client', 
        on_delete=models.CASCADE, 
        related_name="assessment_action_items"  # Changed from "action_items"
    )
    category = models.ForeignKey(
        'branding_and_category.ClientCategory', 
        on_delete=models.CASCADE, 
        related_name="assessment_action_items"  # Changed from "action_items"
    )
    title            = models.CharField(max_length=500)
    description      = models.TextField(blank=True)
    is_ai_generated  = models.BooleanField(default=False)
    ai_suggestion    = models.ForeignKey(
        AIGenerationLog,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="action_items",
    )
    sort_order  = models.IntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "action_items"
        indexes  = [models.Index(fields=["client", "category", "is_active"])]
        ordering = ["sort_order"]

    def __str__(self):
        return self.title[:80]


class AnswerActionItemMapping(models.Model):
    """
    Many-to-many: one answer choice can trigger multiple action items,
    and the same action item can be triggered by multiple answer choices.

    Schema doc: GROUP 8 — answer_action_item_mapping table
    """

    answer_choice = models.ForeignKey(AnswerChoice, on_delete=models.CASCADE, related_name="action_item_mappings")
    action_item   = models.ForeignKey(ActionItem,   on_delete=models.CASCADE, related_name="answer_mappings")
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "answer_action_item_mapping"
        unique_together = [("answer_choice", "action_item")]
        indexes         = [models.Index(fields=["answer_choice"])]

    def __str__(self):
        return f"Choice#{self.answer_choice_id} → ActionItem#{self.action_item_id}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 9 — GUEST SESSIONS & RESPONSES
# ═══════════════════════════════════════════════════════════════════════════════

class AssessmentSession(models.Model):
    """
    One row per guest per assessment attempt.
    assessment_id is locked at session start — never changes even if the
    client later switches their active assessment.

    Schema doc: GROUP 9 — assessment_sessions table
    """

    STATUS_CHOICES = [
        ("started",     "Started"),
        ("in_progress", "In Progress"),
        ("completed",   "Completed"),
        ("expired",     "Expired"),
    ]

    guest        = models.ForeignKey(Guest,      on_delete=models.CASCADE, related_name="sessions")
    assessment   = models.ForeignKey(Assessment, on_delete=models.PROTECT,  related_name="sessions")
    client       = models.ForeignKey(Client,     on_delete=models.CASCADE,  related_name="sessions")
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="started")
    started_at   = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at   = models.DateTimeField()          # set = last_activity_at + 90 days in save()
    password_created = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_sessions"
        indexes  = [
            models.Index(fields=["assessment", "status"]),
            models.Index(fields=["status", "expires_at"]),   # expiry cron job
            models.Index(fields=["guest", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=90)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session#{self.pk} — {self.guest} ({self.status})"


class GuestResponse(models.Model):
    """
    One row per question answered per session.
    points_awarded is a SNAPSHOT — frozen at answer time, never recalculated.

    Schema doc: GROUP 9 — guest_responses table (named assessment_responses in Phase 0 doc)
    """

    session       = models.ForeignKey(AssessmentSession, on_delete=models.CASCADE, related_name="responses")
    question      = models.ForeignKey(Question,          on_delete=models.PROTECT,  related_name="responses")
    answer_choice = models.ForeignKey(AnswerChoice,      on_delete=models.PROTECT,  related_name="responses")
    points_awarded = models.DecimalField(
        max_digits=6, decimal_places=2,
        help_text="SNAPSHOT of answer_choice.point_value at time of answering."
    )
    answered_at  = models.DateTimeField(auto_now=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "guest_responses"
        unique_together = [("session", "question")]
        indexes         = [models.Index(fields=["session"])]

    def save(self, *args, **kwargs):
        # Snapshot point value on first save only
        if not self.pk:
            self.points_awarded = self.answer_choice.point_value
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session#{self.session_id} Q#{self.question_id} → {self.points_awarded}pts"


class AssessmentResponseScore(models.Model):
    """
    Pre-computed per-response score for progressive scoring UI.
    OneToOne with GuestResponse; written / updated by the scoring engine.

    Schema doc: GROUP 9 — assessment_response_score table (Phase 0 doc)
    """

    response       = models.OneToOneField(GuestResponse, on_delete=models.CASCADE, related_name="score")
    points_awarded = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        db_table = "assessment_response_scores"

    def __str__(self):
        return f"Score for Response#{self.response_id}: {self.points_awarded}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 10 — SCORING RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

class SessionCategoryScore(models.Model):
    """
    Calculated automatically when the guest submits.
    One row per category per session.

    Schema doc: GROUP 10 — session_category_scores table
    """

    LABEL_CHOICES = [
        ("critical",    "Critical"),
        ("mediocre",    "Mediocre"),
        ("exceptional", "Exceptional"),
        ("unscored",    "Unscored"),
    ]

    session       = models.ForeignKey(AssessmentSession, on_delete=models.CASCADE, related_name="category_scores")
    category      = models.ForeignKey(ClientCategory,    on_delete=models.CASCADE, related_name="session_scores")
    raw_score     = models.DecimalField(max_digits=8, decimal_places=2)
    max_possible  = models.DecimalField(max_digits=8, decimal_places=2)
    percentage    = models.DecimalField(max_digits=5, decimal_places=2)
    label         = models.CharField(max_length=50, choices=LABEL_CHOICES)
    calculated_at = models.DateTimeField(auto_now_add=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "session_category_scores"
        unique_together = [("session", "category")]
        indexes         = [models.Index(fields=["session"])]

    def __str__(self):
        return f"Session#{self.session_id} {self.category.name}: {self.percentage}% — {self.label}"


class SessionOverallScore(models.Model):
    """
    One row per completed session — the headline score across all categories.

    Schema doc: GROUP 10 — session_overall_scores table
    """

    LABEL_CHOICES = SessionCategoryScore.LABEL_CHOICES

    session       = models.OneToOneField(AssessmentSession, on_delete=models.CASCADE, related_name="overall_score")
    raw_score     = models.DecimalField(max_digits=8, decimal_places=2)
    max_possible  = models.DecimalField(max_digits=8, decimal_places=2)
    percentage    = models.DecimalField(max_digits=5, decimal_places=2)
    label         = models.CharField(max_length=50, choices=LABEL_CHOICES)
    calculated_at = models.DateTimeField(auto_now_add=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_overall_scores"

    def __str__(self):
        return f"Session#{self.session_id} Overall: {self.percentage}% — {self.label}"
