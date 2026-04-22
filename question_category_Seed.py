"""
========================================================================
FILE 3 of 3  —  apps/users/seed_question_category.py
========================================================================
Run AFTER  python manage.py migrate  AND after the main seed.py so that
assessments, categories, and questions already exist in the database.

Command:
    python manage.py shell < apps/users/seed_question_category.py

What it creates:
    One QuestionCategory row for every active question, linking it to:
      - its assessment
      - its category (from question.category_id)
      - its sort_order (from question.sort_order)

    This populates the table to reflect the spec:
      Assessment → many Categories → many Questions per Category
========================================================================
"""

import os
import django

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from django.db import transaction
from assessment.models import Question
from branding_and_category.models import QuestionCategory



@transaction.atomic
def run():
    print("🌱  Seeding question_category table …\n")

    # Fetch all active questions with their assessment and category
    questions = (
        Question.objects
        .select_related("assessment", "category")
        .filter(is_active=True)
        .order_by("assessment_id", "category__sort_order", "sort_order")
    )

    if not questions.exists():
        print("  ⚠  No active questions found. Run seed.py first.")
        return

    created_count  = 0
    existing_count = 0
    current_assessment = None
    current_category   = None

    for q in questions:

        # ── Print grouping headers for readability ─────────────────────
        if q.assessment != current_assessment:
            current_assessment = q.assessment
            current_category   = None
            print(f"\n  Assessment: '{q.assessment.title}'")

        if q.category != current_category:
            current_category = q.category
            print(f"    Category: '{q.category.name}'")

        # ── Create the question_category row ───────────────────────────
        obj, created = QuestionCategory.objects.get_or_create(
            assessment = q.assessment,
            category   = q.category,
            question   = q,
            defaults   = dict(sort_order=q.sort_order),
        )

        if created:
            created_count += 1
            print(f"      ✓ Q#{q.pk:>3}  '{q.question_text[:60]}'  (sort={q.sort_order})")
        else:
            existing_count += 1
            print(f"      –  Q#{q.pk:>3}  already exists, skipped.")

    # ── Summary ────────────────────────────────────────────────────────
    total = QuestionCategory.objects.count()
    print(
        f"\n🎉  Done."
        f"\n    Rows created  : {created_count}"
        f"\n    Already existed: {existing_count}"
        f"\n    Total in table : {total}"
    )

    # # ── Quick verification printout ────────────────────────────────────
    # print("\n  Verification — grouped view:")
    # from apps.users.models import Assessment
    # for assessment in Assessment.objects.filter(is_active=True):
    #     print(f"\n  [{assessment.title}]")
    #     rows = (
    #         QuestionCategory.objects
    #         .filter(assessment=assessment)
    #         .select_related("category", "question")
    #         .order_by("category__sort_order", "sort_order")
    #     )
    #     current_cat = None
    #     for row in rows:
    #         if row.category != current_cat:
    #             current_cat = row.category
    #             print(f"    Category: {row.category.name}")
    #         print(f"      → {row.question.question_text[:65]}")


if __name__ == "__main__":
    run()
