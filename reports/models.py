from django.db import models



# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 11 — REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

class Report(models.Model):
    """
    One row per completed guest session.
    Tracks the full report lifecycle: draft → approved → sent.
    Locked after first send — resend only, no editing.

    Schema doc: GROUP 11 — reports table
    """

    STATUS_CHOICES = [
        ("draft",    "Draft"),
        ("approved", "Approved"),
        ("sent",     "Sent"),
    ]

    # Use string references for all ForeignKeys
    session             = models.OneToOneField(
        'assessment.AssessmentSession', 
        on_delete=models.CASCADE, 
        related_name="report"
    )
    client              = models.ForeignKey(
        'users.Client', 
        on_delete=models.CASCADE, 
        related_name="reports"
    )
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    pdf_url             = models.URLField(max_length=500, blank=True)
    is_locked           = models.BooleanField(default=False)
    generated_at        = models.DateTimeField(null=True, blank=True)
    last_regenerated_at = models.DateTimeField(null=True, blank=True)
    approved_at         = models.DateTimeField(null=True, blank=True)
    sent_at             = models.DateTimeField(null=True, blank=True)
    sent_by             = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sent_reports",
    )
    last_resent_at = models.DateTimeField(null=True, blank=True)
    resend_count   = models.IntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reports"
        indexes  = [
            models.Index(fields=["client", "status"]),
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        return f"Report#{self.pk} for Session#{self.session_id} ({self.status})"

class ReportActionItem(models.Model):
    """
    Snapshot of action items at report generation time.
    Client edits stored in client_edited_* without touching master data.
    """

    report              = models.ForeignKey('reports.Report', on_delete=models.CASCADE, related_name="report_action_items")
    action_item         = models.ForeignKey('assessment.ActionItem', on_delete=models.CASCADE, related_name="report_action_items")
    category            = models.ForeignKey('branding_and_category.ClientCategory', on_delete=models.CASCADE, related_name="report_action_items")
    title_snapshot      = models.CharField(max_length=500)
    description_snapshot = models.TextField(blank=True)
    client_edited_title = models.CharField(max_length=500, blank=True)
    client_edited_desc  = models.TextField(blank=True)
    sort_order          = models.IntegerField(default=0)
    is_included         = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_action_items"
        indexes  = [models.Index(fields=["report", "is_included"])]
        ordering = ["sort_order"]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.title_snapshot = self.action_item.title
            self.description_snapshot = self.action_item.description
        super().save(*args, **kwargs)

    def display_title(self):
        return self.client_edited_title or self.title_snapshot

    def display_desc(self):
        return self.client_edited_desc or self.description_snapshot

    def __str__(self):
        return f"Report#{self.report_id} → {self.display_title()[:60]}"

class ReportAnswerActionItem(models.Model):
    """
    Audit table: records which specific answer choice triggered which action item
    for a given report. Written during report generation.
    """

    report        = models.ForeignKey('reports.Report', on_delete=models.CASCADE, related_name="answer_action_items")
    session       = models.ForeignKey('assessment.AssessmentSession', on_delete=models.CASCADE, related_name="answer_action_items")
    answer_choice = models.ForeignKey('assessment.AnswerChoice', on_delete=models.CASCADE, related_name="report_answer_items")
    action_item   = models.ForeignKey('assessment.ActionItem', on_delete=models.CASCADE, related_name="report_answer_items")

    class Meta:
        db_table = "report_answer_action_items"
        unique_together = [("report", "answer_choice", "action_item")]

    def __str__(self):
        return f"Report#{self.report_id} Choice#{self.answer_choice_id}→Item#{self.action_item_id}"


class ReportUniqueActionItem(models.Model):
    """
    De-duplicated final list of action items to display in a report.
    Client can reorder via sort_order.
    """

    report      = models.ForeignKey('reports.Report', on_delete=models.CASCADE, related_name="unique_action_items")
    action_item = models.ForeignKey('assessment.ActionItem', on_delete=models.CASCADE, related_name="unique_report_items")
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = "report_unique_action_items"
        ordering = ["sort_order"]

    def __str__(self):
        return f"Report#{self.report_id} → {self.action_item.title[:60]}"

class MiniOffer(models.Model):
    """
    AI-generated sales CTA at the end of the report.
    One per report. Locked when report is sent.
    """

    report          = models.OneToOneField('reports.Report', on_delete=models.CASCADE, related_name="mini_offer")
    headline        = models.CharField(max_length=500, blank=True)
    body_text       = models.TextField(blank=True)
    cta_pay_label   = models.CharField(max_length=255, blank=True)
    cta_pay_url     = models.URLField(max_length=500, blank=True)
    cta_appeal_label = models.CharField(max_length=255, blank=True)
    cta_appeal_url  = models.URLField(max_length=500, blank=True)
    is_ai_generated = models.BooleanField(default=False)
    client_edited   = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mini_offers"

    def __str__(self):
        return f"MiniOffer for Report#{self.report_id}: {self.headline[:60]}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 12 — REPORT SETTINGS & THEMES
# ═══════════════════════════════════════════════════════════════════════════════

class ReportTheme(models.Model):
    """
    Provider-managed visual theme library. Clients choose from these.
    """

    name        = models.CharField(max_length=100, unique=True)
    preview_url = models.URLField(max_length=500, blank=True)
    is_active   = models.BooleanField(default=True)
    sort_order  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_themes"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class ClientReportSettings(models.Model):
    """
    One row per client. Theme, logo, colors, fonts, chart type.
    Applied to all reports generated for this client.
    """

    CHART_CHOICES = [
        ("bar",   "Bar Chart"),
        ("pie",   "Pie Chart"),
        ("gauge", "Gauge Meter"),
    ]

    client          = models.OneToOneField('users.Client', on_delete=models.CASCADE, related_name="report_settings")
    theme           = models.ForeignKey(ReportTheme, on_delete=models.SET_NULL, null=True, blank=True)
    logo_url        = models.URLField(max_length=500, blank=True)
    primary_color   = models.CharField(max_length=7, blank=True)
    secondary_color = models.CharField(max_length=7, blank=True)
    heading_font    = models.CharField(max_length=100, blank=True)
    body_font       = models.CharField(max_length=100, blank=True)
    score_chart_type = models.CharField(max_length=50, choices=CHART_CHOICES, default="bar")
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_report_settings"

    def __str__(self):
        return f"ReportSettings for {self.client.full_name}"
