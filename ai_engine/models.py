from django.db import models


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 13 — AI ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AIPromptTemplate(models.Model):
    """
    Database-driven prompt storage — provider edits prompts from admin panel
    without code deployment. Version increments on each edit.
    """

    USE_CASE_CHOICES = [
        ("action_item_suggestion", "Action Item Suggestion"),
        ("mini_offer_suggestion",  "Mini Offer Suggestion"),
        ("category_mapping",       "Category Mapping"),
    ]

    use_case    = models.CharField(max_length=100, unique=True, choices=USE_CASE_CHOICES)
    prompt_text = models.TextField()
    model       = models.CharField(max_length=100)
    version     = models.IntegerField(default=1)
    is_active   = models.BooleanField(default=True)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_prompt_templates"

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = AIPromptTemplate.objects.get(pk=self.pk)
                if old.prompt_text != self.prompt_text:
                    self.version = old.version + 1
                else:
                    self.version = old.version
            except AIPromptTemplate.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.use_case} v{self.version} ({self.model})"


class AIGenerationLog(models.Model):
    """
    Every AI call recorded for debugging, quality analysis, and cost tracking.
    Append-only — never update rows.
    """

    ACTION_CHOICES = [
        ("accepted", "Accepted"),
        ("edited",   "Edited"),
        ("rejected", "Rejected"),
        ("pending",  "Pending"),
    ]

    prompt_template = models.ForeignKey('AIPromptTemplate', on_delete=models.PROTECT, related_name="logs")
    use_case        = models.CharField(max_length=100)
    client          = models.ForeignKey('users.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_logs")
    session         = models.ForeignKey(
        'assessment.AssessmentSession',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="ai_logs"
    )
    report          = models.ForeignKey(
        'reports.Report',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="ai_logs"
    )
    context_payload = models.JSONField(null=True, blank=True)
    raw_response    = models.TextField(blank=True)
    parsed_output   = models.JSONField(null=True, blank=True)
    client_action   = models.CharField(max_length=20, choices=ACTION_CHOICES, default="pending")
    model_used      = models.CharField(max_length=100, blank=True)
    tokens_used     = models.IntegerField(null=True, blank=True)
    generated_at    = models.DateTimeField(auto_now_add=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_generation_log"
        indexes  = [
            models.Index(fields=["use_case", "generated_at"]),
            models.Index(fields=["session"]),
            models.Index(fields=["client"]),
            models.Index(fields=["report"]),
        ]

    def __str__(self):
        return f"AI:{self.use_case} @ {self.generated_at:%Y-%m-%d %H:%M}"