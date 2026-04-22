"""
Insider Access — seed.py
========================
Run after `python manage.py migrate` to populate the DB with Phase 0
POC testing data.

Usage:
    python manage.py shell < apps/users/seed.py
  or add to a management command / call from AppConfig.ready() in dev.

Creates:
  • 1 Provider
  • 1 Partner  (Podcast Pros)
  • 1 Client   (John Doe — PodcastPros client)
  • 1 Guest    (Jane Smith)
  • ProviderMasterCategories (8 standard categories)
  • 1 Assessment with 3 categories, questions, answer choices, thresholds
  • AnswerActionItemMappings
  • 1 completed AssessmentSession + GuestResponses
  • AIPromptTemplates (3 use cases)
  • NotificationEventTypes
  • 1 SubscriptionPlan + PartnerSubscription
  • 1 ReportTheme
"""

import os
import django
from datetime import date, timedelta

# ── Bootstrap Django if running as a standalone script ─────────────────────────
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from django.utils import timezone
from django.db import transaction
from users.models import (
    User, UserLayerMembership,
    Provider, Partner, Client, PartnerClient, Guest)

from assessment.models import (
     ClientCategory,
    Assessment, ScoringThreshold,
    Question, AnswerChoice, QuestionAnswer,
    ActionItem, AnswerActionItemMapping,
    AssessmentSession, GuestResponse, AssessmentResponseScore,
    SessionCategoryScore, SessionOverallScore)

from reports.models import(
    
    Report, ReportActionItem, ReportAnswerActionItem,
    ReportUniqueActionItem, MiniOffer,
    ReportTheme, ClientReportSettings,)

from branding_and_category.models import (
    MenuItem,
    PartnerBranding,
    ProviderMasterCategory,)

from ai_engine.models import (
    AIPromptTemplate, AIGenerationLog,)

from billing_and_notification.models import (
    NotificationEventType, NotificationTemplate,
    SubscriptionPlan, PartnerSubscription,
)


@transaction.atomic
def run():
    print("🌱  Seeding Phase 0 POC data …")

    # ──────────────────────────────────────────────────────────────────────────
    # USERS
    # ──────────────────────────────────────────────────────────────────────────
    provider_admin, _ = User.objects.get_or_create(
        email="admin@insideraccess.com",
        defaults=dict(is_staff=True, is_superuser=True, email_verified=True),
    )
    provider_admin.set_password("Admin@1234!")
    provider_admin.save()

    partner_owner_user, _ = User.objects.get_or_create(
        email="owner@podcastpros.com",
        defaults=dict(email_verified=True),
    )
    partner_owner_user.set_password("Partner@1234!")
    partner_owner_user.save()

    client_user, _ = User.objects.get_or_create(
        email="john@podcasthost.com",
        defaults=dict(email_verified=True),
    )
    client_user.set_password("Client@1234!")
    client_user.save()

    guest_user, _ = User.objects.get_or_create(
        email="jane@guestco.com",
        defaults=dict(email_verified=True),
    )
    guest_user.set_password("Guest@1234!")
    guest_user.save()

    print("  ✓ Users created")

    # ──────────────────────────────────────────────────────────────────────────
    # PROVIDER
    # ──────────────────────────────────────────────────────────────────────────
    provider, _ = Provider.objects.get_or_create(
        domain="insideraccess.com",
        defaults=dict(name="Insider Access", is_active=True),
    )
    print("  ✓ Provider created")

    # ──────────────────────────────────────────────────────────────────────────
    # PARTNER — Podcast Pros
    # ──────────────────────────────────────────────────────────────────────────
    partner, _ = Partner.objects.get_or_create(
        slug="podcastpros",
        defaults=dict(
            provider=provider,
            company_name="Podcast Pros",
            status="active",
            license_start=date.today(),
            approved_at=timezone.now(),
            approved_by=provider_admin,
        ),
    )

    PartnerBranding.objects.get_or_create(
        partner=partner,
        defaults=dict(
            primary_color="#1F4E79",
            secondary_color="#2E75B6",
            font_family="Inter, sans-serif",
            custom_subdomain="podcastpros",
            sender_email="hello@podcastpros.com",
            sender_name="Podcast Pros",
            dns_verified=False,
        ),
    )

    UserLayerMembership.objects.get_or_create(
        user=partner_owner_user,
        layer="partner",
        entity_id=partner.pk,
        defaults=dict(role_type="owner", is_active=True),
    )
    print("  ✓ Partner + Branding created")

    # ──────────────────────────────────────────────────────────────────────────
    # CLIENT — John Doe
    # ──────────────────────────────────────────────────────────────────────────
    client, _ = Client.objects.get_or_create(
        full_name="John Doe",
        defaults=dict(
            company_name="The Podcast Show",
            industry="Media & Entertainment",
            status="active",
        ),
    )

    PartnerClient.objects.get_or_create(
        partner=partner,
        client=client,
        defaults=dict(status="active"),
    )

    UserLayerMembership.objects.get_or_create(
        user=client_user,
        layer="client",
        entity_id=client.pk,
        defaults=dict(role_type="owner", is_active=True),
    )
    print("  ✓ Client created")

    # ──────────────────────────────────────────────────────────────────────────
    # GUEST — Jane Smith
    # ──────────────────────────────────────────────────────────────────────────
    guest, _ = Guest.objects.get_or_create(
        email="jane@guestco.com",
        defaults=dict(
            user=guest_user,
            first_name="Jane",
            last_name="Smith",
            company_name="Guest Co.",
        ),
    )
    print("  ✓ Guest created")

    # ──────────────────────────────────────────────────────────────────────────
    # PROVIDER MASTER CATEGORIES
    # ──────────────────────────────────────────────────────────────────────────
    master_cats_data = [
        ("Content Strategy",      "How well the guest plans and structures content."),
        ("Audience Growth",       "Strategies for growing and engaging an audience."),
        ("Monetisation",          "Revenue generation from podcast/media activities."),
        ("Production Quality",    "Technical quality of audio, video, and editing."),
        ("Guest Management",      "How the host manages guest relationships."),
        ("Distribution",          "Platform reach and cross-publishing strategies."),
        ("Analytics & Reporting", "Use of data to inform content decisions."),
        ("Brand & Identity",      "Consistency and clarity of personal/brand identity."),
    ]
    master_cats = {}
    for i, (name, desc) in enumerate(master_cats_data, 1):
        obj, _ = ProviderMasterCategory.objects.get_or_create(
            name=name,
            defaults=dict(description=desc, is_active=True, sort_order=i * 10),
        )
        master_cats[name] = obj
    print(f"  ✓ {len(master_cats)} ProviderMasterCategories seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # ASSESSMENT
    # ──────────────────────────────────────────────────────────────────────────
    assessment, _ = Assessment.objects.get_or_create(
        client=client,
        title="Podcast Guest Readiness Check",
        defaults=dict(
            industry="Media & Entertainment",
            status="active",
            is_active=True,
            activated_at=timezone.now(),
        ),
    )
    print("  ✓ Assessment created")

    # ──────────────────────────────────────────────────────────────────────────
    # CLIENT CATEGORIES (3 for POC)
    # ──────────────────────────────────────────────────────────────────────────
    cat_defs = [
        ("Content Quality",     "How prepared and structured the guest's content is.",   master_cats["Content Strategy"],   33.33, 10),
        ("Audience Fit",        "How well the guest aligns with the host's audience.",    master_cats["Audience Growth"],    33.33, 20),
        ("Technical Readiness", "Mic, camera, environment, and recording setup quality.", master_cats["Production Quality"], 33.34, 30),
    ]
    categories = {}
    for name, desc, master, weight, order in cat_defs:
        cat, _ = ClientCategory.objects.get_or_create(
            assessment=assessment,
            name=name,
            defaults=dict(
                client=client,
                description=desc,
                master_category=master,
                weight_percentage=weight,
                sort_order=order,
                is_active=True,
            ),
        )
        categories[name] = cat

    # ── Scoring Thresholds ────────────────────────────────────────────────────
    threshold_defs = [
        # (category_name_or_None, label, min, max)
        ("Content Quality",     "critical",    0,  40),
        ("Content Quality",     "mediocre",   40,  70),
        ("Content Quality",     "exceptional",70, 100),
        ("Audience Fit",        "critical",    0,  40),
        ("Audience Fit",        "mediocre",   40,  70),
        ("Audience Fit",        "exceptional",70, 100),
        ("Technical Readiness", "critical",    0,  40),
        ("Technical Readiness", "mediocre",   40,  70),
        ("Technical Readiness", "exceptional",70, 100),
        (None,                  "critical",    0,  40),   # overall
        (None,                  "mediocre",   40,  70),   # overall
        (None,                  "exceptional",70, 100),   # overall
    ]
    for cat_name, label, mn, mx in threshold_defs:
        cat_obj = categories.get(cat_name) if cat_name else None
        ScoringThreshold.objects.get_or_create(
            assessment=assessment,
            category=cat_obj,
            label=label,
            defaults=dict(min_score=mn, max_score=mx),
        )
    print("  ✓ Categories + Thresholds seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # QUESTIONS CATEGORY
    # ──────────────────────────────────────────────────────────────────────────

    

    # ──────────────────────────────────────────────────────────────────────────
    # QUESTIONS & ANSWER CHOICES
    # ──────────────────────────────────────────────────────────────────────────
    q_defs = [
        # (category_name, question_text, is_required, sort, [(choice_text, points)])
        ("Content Quality",
         "How many podcast episodes have you published?",
         True, 10,
         [("None yet", 0), ("1–10 episodes", 2), ("11–50 episodes", 4), ("50+ episodes", 6)]),

        ("Content Quality",
         "Do you have a clear topic or niche for your podcast?",
         True, 20,
         [("No clear niche", 0), ("Somewhat defined", 2), ("Very clearly defined", 4)]),

        ("Audience Fit",
         "Who is your target audience?",
         True, 10,
         [("Not defined yet", 0), ("Broad/general audience", 2), ("Specific niche audience", 4)]),

        ("Audience Fit",
         "How do you currently grow your audience?",
         True, 20,
         [("No active strategy", 0), ("Social media only", 2), ("Multiple channels", 4), ("Paid + organic strategy", 6)]),

        ("Technical Readiness",
         "What microphone do you use?",
         True, 10,
         [("Built-in laptop/phone mic", 0), ("Basic USB mic", 2), ("Dedicated XLR mic", 4)]),

        ("Technical Readiness",
         "Do you record in a quiet, controlled environment?",
         True, 20,
         [("No — lots of background noise", 0), ("Sometimes", 2), ("Yes — always", 4)]),
    ]

    questions = {}
    all_choices = {}
    for cat_name, q_text, required, order, choices in q_defs:
        q, _ = Question.objects.get_or_create(
            assessment=assessment,
            question_text=q_text,
            defaults=dict(
                category=categories[cat_name],
                is_required=required,
                sort_order=order,
                is_active=True,
            ),
        )
        questions[q_text[:30]] = q
        for c_order, (c_text, pts) in enumerate(choices, 1):
            ch, _ = AnswerChoice.objects.get_or_create(
                question=q,
                choice_text=c_text,
                defaults=dict(point_value=pts, sort_order=c_order * 10, is_active=True),
            )
            all_choices[f"{q_text[:30]}|{c_text}"] = ch
            QuestionAnswer.objects.get_or_create(question=q, answer_choice=ch)

    print("  ✓ Questions + AnswerChoices seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # ACTION ITEMS & MAPPINGS
    # ──────────────────────────────────────────────────────────────────────────
    ai_defs = [
        # (category_name, title, description, sort)
        ("Content Quality",
         "Launch your first 3 episodes",
         "Commit to recording and publishing at least 3 episodes to establish a content baseline.",
         10),
        ("Content Quality",
         "Define your podcast niche",
         "Write a one-sentence mission statement for your podcast to sharpen your content focus.",
         20),
        ("Audience Fit",
         "Create a listener persona",
         "Document your ideal listener's demographics, interests, and listening habits.",
         10),
        ("Audience Fit",
         "Diversify your audience channels",
         "Identify 2–3 distribution platforms beyond your primary one and publish to all of them.",
         20),
        ("Technical Readiness",
         "Upgrade your microphone",
         "Invest in a dedicated USB or XLR microphone to eliminate background noise artifacts.",
         10),
        ("Technical Readiness",
         "Soundproof your recording space",
         "Add soft furnishings or acoustic panels to your recording environment to reduce echo.",
         20),
    ]

    action_items = {}
    for cat_name, title, desc, order in ai_defs:
        ai, _ = ActionItem.objects.get_or_create(
            client=client,
            title=title,
            defaults=dict(
                category=categories[cat_name],
                description=desc,
                is_ai_generated=False,
                sort_order=order,
                is_active=True,
            ),
        )
        action_items[title] = ai

    # Map low-scoring answer choices to action items
    mapping_defs = [
        ("How many podcast episodes have you published?|None yet",      "Launch your first 3 episodes"),
        ("How many podcast episodes have you published?|1–10 episodes", "Launch your first 3 episodes"),
        ("Do you have a clear topic or niche for your podcast?|No clear niche", "Define your podcast niche"),
        ("Who is your target audience?|Not defined yet",                "Create a listener persona"),
        ("How do you currently grow your audience?|No active strategy", "Diversify your audience channels"),
        ("What microphone do you use?|Built-in laptop/phone mic",       "Upgrade your microphone"),
        ("Do you record in a quiet, controlled environment?|No — lots of background noise", "Soundproof your recording space"),
    ]
    for choice_key, item_title in mapping_defs:
        choice_key_short = choice_key  # already shortened above; need original form
        # Re-fetch by matching
        q_text_short = choice_key.split("|")[0]
        c_text       = choice_key.split("|")[1]
        ch = all_choices.get(choice_key)
        if ch and item_title in action_items:
            AnswerActionItemMapping.objects.get_or_create(
                answer_choice=ch,
                action_item=action_items[item_title],
            )

    print("  ✓ ActionItems + Mappings seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # SESSION + RESPONSES (completed, for report generation testing)
    # ──────────────────────────────────────────────────────────────────────────
    session, created = AssessmentSession.objects.get_or_create(
        guest=guest,
        assessment=assessment,
        defaults=dict(
            client=client,
            status="completed",
            last_activity_at=timezone.now(),
            completed_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=90),
            password_created=False,
        ),
    )

    if created:
        # Select mid-range answers for a "mediocre" overall result
        response_choices = [
            ("How many podcast episodes have you published?",      "1–10 episodes"),
            ("Do you have a clear topic or niche for your podcast?","Somewhat defined"),
            ("Who is your target audience?",                        "Broad/general audience"),
            ("How do you currently grow your audience?",            "Social media only"),
            ("What microphone do you use?",                         "Basic USB mic"),
            ("Do you record in a quiet, controlled environment?",   "Sometimes"),
        ]
        for q_text, c_text in response_choices:
            q_key = q_text[:30]
            key   = f"{q_key}|{c_text}"
            ch    = all_choices.get(key)
            if ch:
                q = questions.get(q_key)
                if q:
                    resp = GuestResponse.objects.create(
                        session=session,
                        question=q,
                        answer_choice=ch,
                        points_awarded=ch.point_value,
                    )
                    AssessmentResponseScore.objects.create(
                        response=resp,
                        points_awarded=ch.point_value,
                    )

        # Category scores
        cat_score_data = [
            ("Content Quality",     4, 10, 40.0, "mediocre"),
            ("Audience Fit",        4, 10, 40.0, "mediocre"),
            ("Technical Readiness", 4, 8,  50.0, "mediocre"),
        ]
        for cat_name, raw, max_p, pct, label in cat_score_data:
            SessionCategoryScore.objects.create(
                session=session,
                category=categories[cat_name],
                raw_score=raw,
                max_possible=max_p,
                percentage=pct,
                label=label,
            )

        SessionOverallScore.objects.create(
            session=session,
            raw_score=12,
            max_possible=28,
            percentage=42.86,
            label="mediocre",
        )

        # Report (draft)
        report = Report.objects.create(
            session=session,
            client=client,
            status="draft",
            is_locked=False,
            generated_at=timezone.now(),
            resend_count=0,
        )

        # Populate report action items from mappings
        triggered = AnswerActionItemMapping.objects.filter(
            answer_choice__in=session.responses.values_list("answer_choice", flat=True)
        ).select_related("action_item__category")
        seen = set()
        for mapping in triggered:
            ai = mapping.action_item
            if ai.pk not in seen:
                ReportActionItem.objects.create(
                    report=report,
                    action_item=ai,
                    category=ai.category,
                    sort_order=ai.sort_order,
                )
                ReportUniqueActionItem.objects.create(
                    report=report,
                    action_item=ai,
                    sort_order=ai.sort_order,
                )
                seen.add(ai.pk)
            ReportAnswerActionItem.objects.create(
                report=report,
                session=session,
                answer_choice=mapping.answer_choice,
                action_item=ai,
            )

        MiniOffer.objects.create(
            report=report,
            headline="Ready to take your podcast to the next level?",
            body_text=(
                "Based on your results, you're building something great. "
                "Our 90-day Podcast Acceleration Programme will take you from mediocre to exceptional. "
                "Let's map your path to 10x audience growth."
            ),
            cta_pay_label="Join the Programme",
            cta_pay_url="https://podcastpros.com/accelerate",
            cta_appeal_label="Book a Free Strategy Call",
            cta_appeal_url="https://podcastpros.com/call",
            is_ai_generated=False,
            client_edited=False,
        )

    print("  ✓ Session + Responses + Scores + Report seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # REPORT THEME + CLIENT REPORT SETTINGS
    # ──────────────────────────────────────────────────────────────────────────
    theme, _ = ReportTheme.objects.get_or_create(
        name="Professional",
        defaults=dict(is_active=True, sort_order=10),
    )
    ReportTheme.objects.get_or_create(
        name="Modern",
        defaults=dict(is_active=True, sort_order=20),
    )
    ReportTheme.objects.get_or_create(
        name="Executive",
        defaults=dict(is_active=True, sort_order=30),
    )

    ClientReportSettings.objects.get_or_create(
        client=client,
        defaults=dict(
            theme=theme,
            primary_color="#1F4E79",
            secondary_color="#2E75B6",
            score_chart_type="bar",
        ),
    )
    print("  ✓ ReportThemes + ClientReportSettings seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # MENU ITEMS (Phase 0 core set)
    # ──────────────────────────────────────────────────────────────────────────
    menu_items_data = [
        # (layer, module, item_key, label, description, sort)
        ("partner", "client_management",   "view_clients",       "View Clients",          "See the list of all clients.", 10),
        ("partner", "client_management",   "add_client",         "Add Client",            "Invite a new client onto the platform.", 20),
        ("partner", "client_management",   "deactivate_client",  "Deactivate Client",     "Suspend a client's access.", 30),
        ("partner", "billing_management",  "view_billing",       "View Billing",          "See subscription and invoice details.", 10),
        ("partner", "billing_management",  "manage_billing",     "Manage Billing",        "Change plan or update payment method.", 20),
        ("client",  "assessment_builder",  "create_assessment",  "Create Assessment",     "Build a new assessment from scratch.", 10),
        ("client",  "assessment_builder",  "edit_assessment",    "Edit Assessment",       "Modify an existing draft assessment.", 20),
        ("client",  "report_management",   "view_report",        "View Report",           "Read a generated guest report.", 10),
        ("client",  "report_management",   "send_report",        "Send Report",           "Dispatch the report to the guest.", 20),
        ("provider","partner_management",  "approve_partner",    "Approve Partner",       "Activate a pending partner application.", 10),
        ("provider","partner_management",  "suspend_partner",    "Suspend Partner",       "Suspend a partner's platform access.", 20),
    ]
    for layer, module, key, label, desc, order in menu_items_data:
        MenuItem.objects.get_or_create(
            item_key=key,
            defaults=dict(layer=layer, module=module, label=label, description=desc, is_active=True, sort_order=order),
        )
    print("  ✓ MenuItems seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # AI PROMPT TEMPLATES
    # ──────────────────────────────────────────────────────────────────────────
    prompt_defs = [
        (
            "action_item_suggestion",
            "claude-sonnet-4-20250514",
            (
                "You are an expert business consultant. Based on the following assessment context, "
                "generate 3–5 specific, actionable recommendations for improvement.\n\n"
                "Industry: {industry}\n"
                "Category: {category_name}\n"
                "Category Description: {category_description}\n"
                "Guest Answers: {answer_summary}\n\n"
                "Return a JSON array of objects with keys: title (string, max 80 chars), "
                "description (string, 1–2 sentences). No markdown, pure JSON only."
            ),
            "Core prompt for generating action item suggestions after assessment completion.",
        ),
        (
            "mini_offer_suggestion",
            "claude-sonnet-4-20250514",
            (
                "You are a persuasive copywriter specialising in service businesses. "
                "Create a compelling mini offer for the following assessment result.\n\n"
                "Client Business: {client_company}\n"
                "Industry: {industry}\n"
                "Overall Score: {overall_percentage}% ({overall_label})\n"
                "Weakest Categories: {weak_categories}\n\n"
                "Return a JSON object with keys: headline (max 100 chars), body_text (2–3 sentences), "
                "cta_pay_label (max 40 chars), cta_appeal_label (max 40 chars). Pure JSON only."
            ),
            "Prompt for generating the mini offer sales CTA at the end of the report.",
        ),
        (
            "category_mapping",
            "claude-sonnet-4-20250514",
            (
                "Map the following client-defined assessment categories to the closest provider master category.\n\n"
                "Client Categories: {client_categories}\n"
                "Master Categories: {master_categories}\n\n"
                "Return a JSON array of objects with keys: client_category_id, master_category_id, "
                "confidence_score (0.0–1.0). Pure JSON only."
            ),
            "Maps client category names to provider master taxonomy for AI context normalisation.",
        ),
    ]
    for use_case, model, prompt, notes in prompt_defs:
        obj, created = AIPromptTemplate.objects.get_or_create(
            use_case=use_case,
            defaults=dict(prompt_text=prompt, model=model, version=1, is_active=True, notes=notes),
        )
        if not created:
            obj.prompt_text = prompt
            obj.model       = model
            obj.notes       = notes
            # Don't call save() here to avoid auto-incrementing version on seed re-run
            AIPromptTemplate.objects.filter(pk=obj.pk).update(prompt_text=prompt, model=model, notes=notes)
    print("  ✓ AIPromptTemplates seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # NOTIFICATION EVENT TYPES
    # ──────────────────────────────────────────────────────────────────────────
    event_defs = [
        ("guest_submitted",          "Guest Submitted Assessment",   "guest",   "Fires when a guest completes and submits the assessment."),
        ("report_generated",         "Report Generated",             "client",  "Fires when the AI has generated the draft report."),
        ("report_sent",              "Report Sent to Guest",         "guest",   "Fires when the client manually sends the report to the guest."),
        ("partner_approved",         "Partner Account Approved",     "partner", "Fires when the provider approves a partner application."),
        ("client_invited",           "Client Invited",               "client",  "Fires when a partner invites a new client."),
        ("contributor_invited",      "Contributor Invited",          "partner", "Fires when an owner invites a contributor."),
        ("password_reset_requested", "Password Reset Requested",     "client",  "Fires when any user requests a password reset link."),
    ]
    for key, label, recipient, desc in event_defs:
        NotificationEventType.objects.get_or_create(
            event_key=key,
            defaults=dict(label=label, recipient=recipient, description=desc, is_active=True),
        )
    print("  ✓ NotificationEventTypes seeded")

    # ──────────────────────────────────────────────────────────────────────────
    # SUBSCRIPTION PLANS + PARTNER SUBSCRIPTION
    # ──────────────────────────────────────────────────────────────────────────
    starter_plan, _ = SubscriptionPlan.objects.get_or_create(
        name="Starter",
        defaults=dict(
            price_monthly=49.00,
            price_annual=470.00,
            max_clients=5,
            max_assessments=2,
            features={"ai_suggestions": False, "white_label": False, "custom_branding": False},
            is_active=True,
        ),
    )
    SubscriptionPlan.objects.get_or_create(
        name="Professional",
        defaults=dict(
            price_monthly=149.00,
            price_annual=1430.00,
            max_clients=25,
            max_assessments=10,
            features={"ai_suggestions": True, "white_label": True, "custom_branding": True},
            is_active=True,
        ),
    )
    SubscriptionPlan.objects.get_or_create(
        name="Enterprise",
        defaults=dict(
            price_monthly=399.00,
            price_annual=3830.00,
            max_clients=None,
            max_assessments=None,
            features={"ai_suggestions": True, "white_label": True, "custom_branding": True, "api_access": True},
            is_active=True,
        ),
    )

    today = date.today()
    PartnerSubscription.objects.get_or_create(
        partner=partner,
        defaults=dict(
            plan=starter_plan,
            status="trialing",
            billing_cycle="monthly",
            current_period_start=today,
            current_period_end=today + timedelta(days=30),
        ),
    )
    print("  ✓ SubscriptionPlans + PartnerSubscription seeded")

    print("\n🎉  Phase 0 seed complete. All POC data is ready.")
    print("\nTest credentials:")
    print("  Provider Admin  →  admin@insideraccess.com   / Admin@1234!")
    print("  Partner Owner   →  owner@podcastpros.com    / Partner@1234!")
    print("  Client          →  john@podcasthost.com     / Client@1234!")
    print("  Guest           →  jane@guestco.com         / Guest@1234!")


if __name__ == "__main__":
    run()
