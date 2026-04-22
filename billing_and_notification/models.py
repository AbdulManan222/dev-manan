from django.db import models


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 14 — NOTIFICATIONS & EMAILS
# ═══════════════════════════════════════════════════════════════════════════════

class NotificationEventType(models.Model):
    """
    Table-driven event registry — new event types without code changes.

    Schema doc: GROUP 14 — notification_event_types table
    """

    RECIPIENT_CHOICES = [
        ("guest",   "Guest"),
        ("client",  "Client"),
        ("partner", "Partner"),
    ]

    event_key   = models.CharField(max_length=100, unique=True)
    label       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    recipient   = models.CharField(max_length=50, choices=RECIPIENT_CHOICES)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_event_types"

    def __str__(self):
        return self.event_key


class NotificationTemplate(models.Model):
    """
    Email template per event type per partner.
    partner=None → provider-level default (fallback).

    Schema doc: GROUP 14 — notification_templates table
    """

    event_type = models.ForeignKey(NotificationEventType, on_delete=models.CASCADE, related_name="templates")
    partner    = models.ForeignKey(
        'users.Partner',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="notification_templates",
        help_text="NULL = provider-level default",
    )
    subject    = models.CharField(max_length=500)
    body_html  = models.TextField()
    body_text  = models.TextField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_templates"
        unique_together = [("event_type", "partner")]

    def __str__(self):
        scope = self.partner.company_name if self.partner else "Default"
        return f"{self.event_type.event_key} [{scope}]"


class NotificationLog(models.Model):
    """
    Complete record of every email sent by the platform.

    Schema doc: GROUP 14 — notification_log table
    """

    STATUS_CHOICES = [
        ("sent",    "Sent"),
        ("failed",  "Failed"),
        ("bounced", "Bounced"),
    ]

    event_type      = models.ForeignKey(NotificationEventType, on_delete=models.PROTECT, related_name="logs")
    template        = models.ForeignKey(NotificationTemplate,  on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    recipient_email = models.EmailField(max_length=255)
    session         = models.ForeignKey('assessment.AssessmentSession', on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_logs")
    report          = models.ForeignKey('reports.Report',     on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_logs")
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES)
    sent_at         = models.DateTimeField()
    sendgrid_msg_id = models.CharField(max_length=255, blank=True)
    error_message   = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_log"
        indexes  = [models.Index(fields=["status", "sent_at"])]

    def __str__(self):
        return f"{self.event_type.event_key} → {self.recipient_email} ({self.status})"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 15 — BILLING & SUBSCRIPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SubscriptionPlan(models.Model):
    """
    Provider-defined subscription tiers for partners.
    Table-driven — provider manages plans from admin panel.

    Schema doc: GROUP 15 — subscription_plans table
    """

    name            = models.CharField(max_length=100, unique=True)
    price_monthly   = models.DecimalField(max_digits=10, decimal_places=2)
    price_annual    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_clients     = models.IntegerField(null=True, blank=True)       # NULL = unlimited
    max_assessments = models.IntegerField(null=True, blank=True)
    features        = models.JSONField(null=True, blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"

    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"


class PartnerSubscription(models.Model):
    """
    One row per partner — their active subscription.
    Stripe IDs link to payment processor (card data never stored here).

    Schema doc: GROUP 15 — partner_subscriptions table
    """

    STATUS_CHOICES = [
        ("active",   "Active"),
        ("past_due", "Past Due"),
        ("cancelled","Cancelled"),
        ("trialing", "Trialing"),
    ]
    CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("annual",  "Annual"),
    ]

    partner               = models.OneToOneField('users.Partner', on_delete=models.CASCADE, related_name="subscription")
    plan                  = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status                = models.CharField(max_length=20, choices=STATUS_CHOICES, default="trialing")
    billing_cycle         = models.CharField(max_length=20, choices=CYCLE_CHOICES, default="monthly")
    current_period_start  = models.DateField()
    current_period_end    = models.DateField()
    stripe_customer_id    = models.CharField(max_length=255, blank=True)
    stripe_sub_id         = models.CharField(max_length=255, blank=True)
    cancelled_at          = models.DateTimeField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_subscriptions"

    def __str__(self):
        return f"{self.partner.company_name} — {self.plan.name} ({self.status})"


class BillingEvent(models.Model):
    """
    Append-only log of every potentially billable platform action.
    Used to generate itemized invoices per partner.

    Schema doc: GROUP 15 — billing_events table
    """

    EVENT_CHOICES = [
        ("assessment_completed", "Assessment Completed"),
        ("report_generated",     "Report Generated"),
        ("report_sent",          "Report Sent"),
    ]

    partner     = models.ForeignKey('users.Partner', on_delete=models.CASCADE, related_name="billing_events")
    client      = models.ForeignKey('users.Client',  on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_events")
    session     = models.ForeignKey('assessment.AssessmentSession', on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_events")
    event_type  = models.CharField(max_length=100, choices=EVENT_CHOICES)
    occurred_at = models.DateTimeField()
    invoice_id  = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_events"
        indexes  = [models.Index(fields=["partner", "occurred_at"])]

    def __str__(self):
        return f"{self.partner.slug} | {self.event_type} @ {self.occurred_at:%Y-%m-%d}"

