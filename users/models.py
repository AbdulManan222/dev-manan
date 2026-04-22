
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — USERS & IDENTITY
# ═══════════════════════════════════════════════════════════════════════════════

class CustomUserManager(BaseUserManager):
    """Manager for email-based authentication (no username field)."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)          # bcrypt via PASSWORD_HASHERS setting
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Single source of truth for every person on the platform.
    Provider admins, partner staff, clients, and guests all have a row here.
    Register in settings.py → AUTH_USER_MODEL = 'users.User'

    Schema doc: GROUP 1 — users table
    """

    # ── Identity ───────────────────────────────────────────────────────────────
    email           = models.EmailField(max_length=255, unique=True)

    # password is inherited from AbstractBaseUser (stored as bcrypt hash)

    # ── Status ─────────────────────────────────────────────────────────────────
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)   # Django admin access
    email_verified  = models.BooleanField(default=False)
    last_login_at   = models.DateTimeField(null=True, blank=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table    = "users"
        verbose_name        = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email


class UserLayerMembership(models.Model):
    """
    Allows one user to belong to multiple layers simultaneously.
    Every time a user is added to provider / partner / client / guest layer,
    a new row is created here.

    Schema doc: GROUP 1 — user_layer_memberships table
    """

    LAYER_CHOICES = [
        ("provider", "Provider"),
        ("partner",  "Partner"),
        ("client",   "Client"),
        ("guest",    "Guest"),
    ]
    ROLE_CHOICES = [
        ("owner",       "Owner"),
        ("contributor", "Contributor"),
    ]

    user        = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    layer       = models.CharField(max_length=20, choices=LAYER_CHOICES)
    entity_id   = models.IntegerField()            # FK to provider/partner/client/guest PK
    role_type   = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active   = models.BooleanField(default=True)

    invited_by  = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sent_invitations",
    )
    invited_at  = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_layer_memberships"
        unique_together = [("user", "layer", "entity_id")]
        indexes = [
            models.Index(fields=["layer", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.layer}:{self.entity_id} ({self.role_type})"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — PLATFORM LAYERS
# ═══════════════════════════════════════════════════════════════════════════════

class Provider(models.Model):
    """
    The Insider Access platform itself. Typically a single row.

    Schema doc: GROUP 2 — providers table
    """

    name       = models.CharField(max_length=255)
    domain     = models.CharField(max_length=255, unique=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "providers"

    def __str__(self):
        return self.name


class Partner(models.Model):
    """
    Companies/agencies that license Insider Access from the provider
    (e.g. Podcast Pros).

    Schema doc: GROUP 2 — partners table
    """

    STATUS_CHOICES = [
        ("active",    "Active"),
        ("inactive",  "Inactive"),
        ("suspended", "Suspended"),
    ]

    provider      = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="partners"
    )
    company_name  = models.CharField(max_length=255)
    slug          = models.SlugField(max_length=100, unique=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    license_start = models.DateField(null=True, blank=True)
    license_end   = models.DateField(null=True, blank=True)
    approved_at   = models.DateTimeField(null=True, blank=True)
    approved_by   = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_partners",
    )
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partners"
        indexes  = [models.Index(fields=["provider", "status"])]

    def __str__(self):
        return self.company_name


class Client(models.Model):
    """
    Podcast hosts / business operators who run assessments and interact
    with guests.

    Schema doc: GROUP 2 — clients table
    """

    STATUS_CHOICES = [
        ("active",    "Active"),
        ("inactive",  "Inactive"),
        ("suspended", "Suspended"),
    ]

    full_name    = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    industry     = models.CharField(max_length=255, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clients"
        indexes  = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.full_name} ({self.company_name})"


class PartnerClient(models.Model):
    """
    Many-to-many join between partners and clients.
    Deactivating only affects this row — client data remains intact.

    Schema doc: GROUP 2 — partner_clients table
    """

    STATUS_CHOICES = [
        ("active",   "Active"),
        ("inactive", "Inactive"),
    ]

    partner        = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="partner_clients")
    client         = models.ForeignKey(Client,  on_delete=models.CASCADE, related_name="partner_clients")
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    added_at       = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "partner_clients"
        unique_together = [("partner", "client")]

    def __str__(self):
        return f"{self.partner.slug} ↔ {self.client.full_name}"


class Guest(models.Model):
    """
    Assessment respondents. They have a User row for auth + this row for profile.

    Schema doc: GROUP 2 — guests table
    """

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name="guest_profile")
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    company_name = models.CharField(max_length=255, blank=True)
    email        = models.EmailField(max_length=255, unique=True)   # fast lookup / dupe detection
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "guests"

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"