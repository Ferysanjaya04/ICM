
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from recommendations.models import CareerRecommendation
from recommendations.tests_api import create_resume


class CareerRecommendationE2ETests(TestCase):
    """
    End-to-end Feature 2:
    Resume DB -> Django API -> AI asli ->
    PostgreSQL -> API detail.
    """

    def test_real_ai_generates_and_persists_top_three(self):
        user = User.objects.create_user(
            username="career_e2e_user",
            password="TestPassword123!",
        )

        cv_text = (
            "Backend Developer with 3 years of experience "
            "building REST API services using Python, Django, "
            "PostgreSQL, Docker, Git and AWS. "
            "Developed scalable microservices and worked "
            "with backend engineering teams."
        )

        resume = create_resume(
            user,
            text=cv_text,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            reverse("recommendation-generate"),
            {"resume_id": str(resume.id)},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
            response.data,
        )

        recommendation = CareerRecommendation.objects.get(
            user=user,
            resume=resume,
        )

        roles = list(
            recommendation.top_roles.all()
        )

        self.assertEqual(len(roles), 3)
        self.assertEqual(
            [role.rank for role in roles],
            [1, 2, 3],
        )
        self.assertEqual(
            len(
                {
                    role.role_title
                    for role in roles
                }
            ),
            3,
        )

        self.assertIsInstance(
            recommendation.profile_summary,
            dict,
        )
        self.assertIsInstance(
            recommendation.detected_skills,
            list,
        )
        self.assertIsInstance(
            recommendation.learning_path,
            list,
        )

        probabilities = (
            recommendation.profile_summary.get(
                "category_probabilities",
                {},
            )
        )

        self.assertEqual(len(probabilities), 3)

        detail_response = client.get(
            reverse(
                "recommendation-detail",
                kwargs={"pk": recommendation.pk},
            )
        )

        self.assertEqual(
            detail_response.status_code,
            200,
        )
        self.assertEqual(
            len(detail_response.data["top_roles"]),
            3,
        )

        print("\nFEATURE 2 E2E RESULT")
        print(
            "DOMINANT CATEGORY:",
            recommendation.dominant_category,
        )

        for role in roles:
            print(
                f"Rank {role.rank}: "
                f"{role.role_title} | "
                f"Skill Match: {role.match_percentage}%"
            )

        print(
            "LEARNING PATHS:",
            len(recommendation.learning_path),
        )
