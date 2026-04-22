from django.db import models
from users.models import Client,UserLayerMembership,User,Partner
from django.utils import timezone



#========================================================================
# GROUP 3 — ROLES & PERMISSIONS
#========================================================================



class MenuItem(models.Model):
    """
    Master list of every permissionable feature/action on the platform.
    Every option that can appear in a user's menu is a row here.

    Schema doc: GROUP 3 — menu_items table
    """

    LAYER_CHOICES = [
        ("provider", "Provider"),
        ("partner",  "Partner"),
        ("client",   "Client"),
    ]

    layer       = models.CharField(max_length=20, choices=LAYER_CHOICES)
    module      = models.CharField(max_length=100)      # e.g. billing_management
    item_key    = models.CharField(max_length=100, unique=True)  # e.g. deactivate_client
    label       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    sort_order  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "menu_items"
        indexes  = [models.Index(fields=["layer", "is_active"])]
        ordering = ["layer", "module", "sort_order"]

    def __str__(self):
        return f"[{self.layer}] {self.item_key}"


class ContributorPermission(models.Model):
    """
    Actual permission grants for contributor users.
    If a contributor has no row for a menu_item, that option is invisible.

    Schema doc: GROUP 3 — contributor_permissions table
    """

    ACCESS_CHOICES = [
        ("view",  "View"),
        ("edit",  "Edit"),
        ("admin", "Admin"),
    ]

    user_layer  = models.ForeignKey(
        UserLayerMembership,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    menu_item   = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="grants",
    )
    access_level = models.CharField(max_length=10, choices=ACCESS_CHOICES)
    granted_by   = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="granted_permissions",
    )
    granted_at   = models.DateTimeField(default=timezone.now)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "contributor_permissions"
        unique_together = [("user_layer", "menu_item")]
        indexes         = [models.Index(fields=["user_layer"])]

    def __str__(self):
        return f"{self.user_layer} → {self.menu_item.item_key} ({self.access_level})"

#========================================================================
# GROUP 4 — BRANDING & WHITE-LABEL
#========================================================================

class PartnerBranding(models.Model):
    """
    One row per partner — everything needed to white-label the platform.

    Schema doc: GROUP 4 — partner_branding table
    """

    partner          = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name="branding")
    logo_url         = models.URLField(max_length=500, blank=True)
    primary_color    = models.CharField(max_length=7, blank=True)    # #RRGGBB
    secondary_color  = models.CharField(max_length=7, blank=True)
    font_family      = models.CharField(max_length=100, blank=True)
    custom_subdomain = models.CharField(max_length=100, unique=True, blank=True)
    sender_email     = models.EmailField(max_length=255, blank=True)
    sender_name      = models.CharField(max_length=255, blank=True)
    dns_verified     = models.BooleanField(default=False)
    dns_verified_at  = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_branding"

    def __str__(self):
        return f"Branding: {self.partner.company_name}"


#========================================================================
# GROUP 5 — INDUSTRY & CATEGORY MAPPING
#========================================================================

class ProviderMasterCategory(models.Model):
    """
    Provider-maintained master taxonomy. Invisible to clients.
    Used by the AI engine for structured category mapping.

    Schema doc: GROUP 5 — provider_master_categories table
    """

    name        = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    sort_order  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "provider_master_categories"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class ClientCategory(models.Model):
    """
    Categories a client creates for a specific assessment.
    Mapped to ProviderMasterCategory in the background for AI context.

    Schema doc: GROUP 5 — client_categories table
    """

    client          = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="categories")
    assessment      = models.ForeignKey("assessment.Assessment", on_delete=models.CASCADE, related_name="categories")
    name            = models.CharField(max_length=255)
    description     = models.TextField(blank=True)
    weight_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Contribution % to overall score. NULL = equal weight."
    )
    master_category = models.ForeignKey(
        ProviderMasterCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="client_categories",
    )
    sort_order  = models.IntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_categories"
        indexes  = [models.Index(fields=["assessment", "is_active"])]
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} (Assessment #{self.assessment_id})"
    






class QuestionCategory(models.Model):
    """
    WHAT THIS TABLE DOES:
    ─────────────────────
    Stores the grouping of questions under categories for a given assessment.

    One assessment has MANY categories.
    One category has MANY questions.

    This table is the explicit record that says:
    "For Assessment #5, Category 'Content Quality' contains
    Questions #12, #13, #14 — in that order."

    The assessment form reads this table to render questions
    grouped under their category headers in the correct order.

    COLUMNS:
    assessment_id  →  which assessment this grouping belongs to
    category_id    →  which category within that assessment
    question_id    →  which question belongs to this category
    sort_order     →  display order of the question within the category
    created_at     →  when this grouping record was created
    updated_at     →  when this record was last updated
        Stores the category grouping of questions for an assessment.

    An assessment has multiple categories.
    Each category has multiple questions.
    This table records which question belongs to which category
    and in what order it appears within that category.
    """

    assessment = models.ForeignKey(
        "assessment.Assessment",
        on_delete=models.CASCADE,
        related_name="question_category_groups",
        help_text="The assessment this grouping belongs to.",
    )
    category = models.ForeignKey(
        "ClientCategory",
        on_delete=models.CASCADE,
        related_name="question_category_groups",
        help_text="The category within the assessment.",
    )
    question = models.ForeignKey(
        "assessment.Question",
        on_delete=models.CASCADE,
        related_name="question_category_groups",
        help_text="The question that belongs to this category.",
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order of this question within the category.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "question_category"
        unique_together = [("assessment", "category", "question")]
        indexes = [
            models.Index(
                fields=["assessment", "category"],
                name="qcat_assessment_category_idx",
            ),
            models.Index(
                fields=["assessment", "category", "sort_order"],
                name="qcat_order_idx",
            ),
        ]
        ordering = ["assessment", "category__sort_order", "sort_order"]

    def __str__(self):
        return (
            f"Assessment#{self.assessment_id} → "
            f"{self.category.name} → "
            f"Q#{self.question_id} (order={self.sort_order})"
        )
