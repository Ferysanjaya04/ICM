
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from resumes.models import Resume
from recommendations.models import CareerRecommendation, TopRole


CV_TEXT = (
    "Backend Developer with 3 years of experience. "
    "Python Django PostgreSQL Docker Git REST API AWS. "
    "Built scalable backend services and microservices."
)


def create_resume(user, text=CV_TEXT):
    """
    Buat resume langsung di database pengujian.

    Isi field file apabila model Resume memilikinya.
    Tidak perlu melakukan upload sungguhan untuk API unit test.
    """
    kwargs = {
        "user": user,
        "extracted_text": text,
    }

    field_names = {
        field.name
        for field in Resume._meta.concrete_fields
    }

    if "cv_file" in field_names:
        kwargs["cv_file"] = "test_career_cv.pdf"

    return Resume.objects.create(**kwargs)


def fake_ai_result():
    return {
        "status": "success",
        "predicted_category": "Backend Developer",
        "detected_skills": [
            "python",
            "django",
            "postgresql",
        ],
        "profile_summary": {
            "top_category": "Backend Developer",
            "all_predicted_categories": [
                "Backend Developer",
                "Python Developer",
                "Java Developer",
            ],
            "category_probabilities": {
                "Backend Developer": 0.60,
                "Python Developer": 0.30,
                "Java Developer": 0.10,
            },
        },
        "learning_path": [
            {
                "rank": 1,
                "role_title": "Backend Developer",
                "suggested_skills": ["kubernetes"],
                "steps": [
                    {
                        "step": 1,
                        "skill": "kubernetes",
                        "activity": "Pelajari dasar Kubernetes.",
                    }
                ],
            }
        ],
        "top_recommendations": [
            {
                "rank": 1,
                "role_title": "Backend Developer",
                "category": "Technology",
                "match_percentage": 80.0,
                "salary_range": "80-150K",
            },
            {
                "rank": 2,
                "role_title": "Python Developer",
                "category": "Technology",
                "match_percentage": 70.0,
                "salary_range": "75-140K",
            },
            {
                "rank": 3,
                "role_title": "Java Developer",
                "category": "Technology",
                "match_percentage": 40.0,
                "salary_range": "70-130K",
            },
        ],
    }


class CareerRecommendationAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="career_user",
            password="TestPassword123!",
        )
        cls.other_user = User.objects.create_user(
            username="other_career_user",
            password="TestPassword123!",
        )

        cls.resume = create_resume(cls.user)
        cls.other_resume = create_resume(cls.other_user)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.generate_url = reverse("recommendation-generate")

    def test_generate_requires_authentication(self):
        anonymous = APIClient()

        response = anonymous.post(
            self.generate_url,
            {"resume_id": str(self.resume.id)},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])
        self.assertEqual(
            CareerRecommendation.objects.count(), 0
        )

    def test_invalid_resume_uuid_rejected(self):
        response = self.client.post(
            self.generate_url,
            {"resume_id": "bukan-uuid"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_use_other_users_resume(self):
        response = self.client.post(
            self.generate_url,
            {"resume_id": str(self.other_resume.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.assertFalse(
            CareerRecommendation.objects.exists()
        )

    def test_short_cv_rejected(self):
        short_resume = create_resume(
            self.user,
            text="Python",
        )

        response = self.client.post(
            self.generate_url,
            {"resume_id": str(short_resume.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    @patch(
        "recommendations.views.recommend_career",
        return_value=fake_ai_result(),
    )
    def test_generate_saves_three_roles_and_learning_path(
        self,
        mocked_ai,
    ):
        response = self.client.post(
            self.generate_url,
            {"resume_id": str(self.resume.id)},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
            response.data,
        )
        mocked_ai.assert_called_once()

        recommendation = CareerRecommendation.objects.get(
            user=self.user,
            resume=self.resume,
        )

        self.assertEqual(
            recommendation.dominant_category,
            "Backend Developer",
        )
        self.assertIsInstance(
            recommendation.learning_path,
            list,
        )
        self.assertEqual(
            len(recommendation.learning_path),
            1,
        )
        self.assertEqual(
            recommendation.profile_summary[
                "category_probabilities"
            ]["Backend Developer"],
            0.60,
        )

        ranks = list(
            recommendation.top_roles.values_list(
                "rank",
                flat=True,
            )
        )

        self.assertEqual(ranks, [1, 2, 3])
        self.assertEqual(
            recommendation.top_roles.count(), 3
        )
        self.assertEqual(
            len(response.data["top_roles"]), 3
        )

    @patch(
        "recommendations.views.recommend_career",
        return_value=fake_ai_result(),
    )
    def test_generate_again_replaces_roles_without_duplicates(
        self,
        mocked_ai,
    ):
        payload = {"resume_id": str(self.resume.id)}

        first = self.client.post(
            self.generate_url,
            payload,
            format="json",
        )
        second = self.client.post(
            self.generate_url,
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)

        self.assertEqual(
            CareerRecommendation.objects.filter(
                user=self.user,
                resume=self.resume,
            ).count(),
            1,
        )

        self.assertEqual(
            TopRole.objects.filter(
                recommendation__user=self.user
            ).count(),
            3,
        )

    @patch(
        "recommendations.views.recommend_career"
    )
    def test_incomplete_ai_result_not_saved(
        self,
        mocked_ai,
    ):
        result = fake_ai_result()
        result["top_recommendations"] = (
            result["top_recommendations"][:2]
        )

        mocked_ai.return_value = result

        response = self.client.post(
            self.generate_url,
            {"resume_id": str(self.resume.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            CareerRecommendation.objects.count(), 0
        )

    @patch(
        "recommendations.views.recommend_career",
        return_value=fake_ai_result(),
    )
    def test_other_user_cannot_read_recommendation(
        self,
        mocked_ai,
    ):
        generated = self.client.post(
            self.generate_url,
            {"resume_id": str(self.resume.id)},
            format="json",
        )

        self.assertEqual(generated.status_code, 201)

        recommendation = CareerRecommendation.objects.get(
            user=self.user,
            resume=self.resume,
        )

        other_client = APIClient()
        other_client.force_authenticate(
            user=self.other_user
        )

        detail_url = reverse(
            "recommendation-detail",
            kwargs={"pk": recommendation.pk},
        )

        response = other_client.get(detail_url)
        self.assertEqual(response.status_code, 404)

    @patch(
        "recommendations.views.recommend_career",
        return_value=fake_ai_result(),
    )
    def test_transaction_rolls_back_if_toprole_save_fails(
        self,
        mocked_ai,
    ):
        original_create = TopRole.objects.create
        counter = {"calls": 0}

        def create_with_failure(**kwargs):
            counter["calls"] += 1

            if counter["calls"] == 2:
                raise RuntimeError(
                    "Simulated database write failure"
                )

            return original_create(**kwargs)

        with patch.object(
            TopRole.objects,
            "create",
            side_effect=create_with_failure,
        ):
            response = self.client.post(
                self.generate_url,
                {"resume_id": str(self.resume.id)},
                format="json",
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            CareerRecommendation.objects.count(), 0
        )
        self.assertEqual(TopRole.objects.count(), 0)

    @patch(
        "recommendations.views.recommend_career",
        return_value=fake_ai_result(),
    )
    def test_get_detail_returns_saved_learning_path(
        self,
        mocked_ai,
    ):
        generated = self.client.post(
            self.generate_url,
            {"resume_id": str(self.resume.id)},
            format="json",
        )

        self.assertEqual(generated.status_code, 201)

        rec = CareerRecommendation.objects.get(
            resume=self.resume,
            user=self.user,
        )

        detail_url = reverse(
            "recommendation-detail",
            kwargs={"pk": rec.pk},
        )

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.data["top_roles"]), 3
        )
        self.assertEqual(
            len(response.data["learning_path"]), 1
        )
