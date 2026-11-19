
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


    def test_evidence_unknown_scores_and_probabilities_survive_history(self):
        from lib import feature2 as engine
        text = "Skills: Python, Django. Projects: Built PRIVATE_EVIDENCE_MARKER using Django. No Docker experience."
        categories = ["Backend Developer", "Python Developer", "Site Reliability Engineer"]
        probabilities = dict(zip(categories, [.7, .2, .05]))
        with patch.object(engine, "predict_career_categories", return_value={
            "status": "success", "predicted_categories": categories, "probabilities": probabilities,
        }):
            result = engine.recommend_career(text)
        self.assertEqual(result["status"], "success", result)
        with patch("recommendations.views.recommend_career", return_value=result):
            response = self.client.post(self.generate_url, {"resume_id": str(self.resume.pk)}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        rec = CareerRecommendation.objects.get(pk=response.data["id"])
        roles = list(rec.top_roles.all())
        self.assertEqual([r.match_details["predicted_category"] for r in roles], categories)
        self.assertEqual([r.match_details["category_probability"] for r in roles], [.7, .2, .05])
        self.assertIsNone(roles[-1].match_percentage)
        self.assertIsNone(response.data["top_roles"][-1]["match_percentage"])
        self.assertFalse(response.data["top_roles"][-1]["skill_match_available"])
        self.assertEqual(response.data["top_roles"][-1]["skill_match_status"], "unknown")
        self.assertIsNone(response.data["top_roles"][-1]["missing_skills"])
        snapshot = response.data
        self.resume.extracted_text = "Skills: Docker, Kubernetes"
        self.resume.save(update_fields=["extracted_text"])
        # Reads must use the saved snapshot, not rerun the parser/model or reference mapping.
        with patch("recommendations.views.recommend_career", side_effect=AssertionError("History must not recompute AI")):
            detail = self.client.get(reverse("recommendation-detail", kwargs={"pk": rec.pk}))
            history = self.client.get(reverse("recommendation-list"))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data, snapshot)
        history_rows = history.data if isinstance(history.data, list) else history.data["results"]
        self.assertEqual(history_rows[0], snapshot)
        # The listed-skill mention may be primary; project evidence must survive too.
        self.assertTrue(any(
            "PRIVATE_EVIDENCE_MARKER" in mention["evidence"]
            for item in rec.profile_summary["cv_understanding"]["skills"]
            for mention in item["evidence_items"]
        ))

    def test_unknown_is_not_persisted_as_a_fabricated_zero(self):
        invalid = fake_ai_result()
        invalid["top_recommendations"][0].update(skill_match_available=False, match_percentage=0)
        with patch("recommendations.views.recommend_career", return_value=invalid):
            response = self.client.post(self.generate_url, {"resume_id": str(self.resume.pk)}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(CareerRecommendation.objects.count(), 0)
        self.assertEqual(TopRole.objects.count(), 0)

    def test_legacy_scores_are_preserved_without_inventing_requirements(self):
        rec = CareerRecommendation.objects.create(user=self.user, resume=self.resume, dominant_category="Historical category")
        role = TopRole.objects.create(recommendation=rec, role_title="Historical role", rank=1, match_percentage=0)
        response = self.client.get(reverse("recommendation-detail", kwargs={"pk": rec.pk}))
        self.assertEqual(response.status_code, 200)
        old_role = response.data["top_roles"][0]
        self.assertIsNone(old_role["match_percentage"])
        self.assertEqual(float(old_role["legacy_match_percentage"]), 0)
        self.assertFalse(old_role["skill_match_available"])
        self.assertEqual(old_role["skill_match_status"], "legacy_unverified")
        self.assertIsNone(old_role["category_probability"])
        self.assertIsNone(old_role["required_skills"])
        role.refresh_from_db()
        self.assertEqual(role.match_details, {})
        self.assertEqual(float(role.match_percentage), 0)

    @patch("recommendations.views.recommend_career", side_effect=RuntimeError("PRIVATE_EVIDENCE_MARKER"))
    def test_engine_failure_does_not_log_or_return_evidence(self, engine):
        with self.assertLogs("recommendations.views", level="ERROR") as logs:
            response = self.client.post(self.generate_url, {"resume_id": str(self.resume.pk)}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("PRIVATE_EVIDENCE_MARKER", "\n".join(logs.output))
        self.assertNotIn("PRIVATE_EVIDENCE_MARKER", str(response.data))


    def test_legacy_salary_and_scores_remain_stored_but_unknown_in_history(self):
        rec=CareerRecommendation.objects.create(user=self.user,resume=self.resume,dominant_category='Historical role')
        row=TopRole.objects.create(recommendation=rec,role_title='Historical role',rank=1,match_percentage=75,salary_range='80-150K')
        with patch('recommendations.views.recommend_career',side_effect=AssertionError('History must not recompute')):
            detail=self.client.get(reverse('recommendation-detail',kwargs={'pk':rec.pk}))
            history=self.client.get(reverse('recommendation-list'))
        self.assertEqual(detail.status_code,200)
        self.assertEqual(history.status_code,200)
        role=detail.data['top_roles'][0]
        self.assertEqual(role['salary_range'],'')
        self.assertEqual(role['legacy_salary_range'],'80-150K')
        self.assertEqual(role['salary_metadata']['status'],'unknown')
        self.assertIsNone(role['salary_metadata']['currency'])
        self.assertEqual(role['requirements_status'],'unknown')
        self.assertEqual(float(role['legacy_match_percentage']),75)
        row.refresh_from_db()
        self.assertEqual(row.salary_range,'80-150K')
        self.assertEqual(float(row.match_percentage),75)
        self.assertEqual(row.match_details,{})

    def test_new_salary_provenance_and_evidence_snapshot_survive_api(self):
        from lib import feature2 as engine
        result=engine.recommend_career('Skills: Python, Django, SQL, Git. Projects: Built a web application for students.')
        self.assertEqual(result['status'],'success')
        with patch('recommendations.views.recommend_career',return_value=result):
            response=self.client.post(self.generate_url,{'resume_id':str(self.resume.pk)},format='json')
        self.assertEqual(response.status_code,201,response.data)
        rec=CareerRecommendation.objects.get(pk=response.data['id'])
        for db_role,api_role in zip(rec.top_roles.all(),response.data['top_roles']):
            self.assertEqual(db_role.match_details['salary_metadata'],api_role['salary_metadata'])
            self.assertEqual(db_role.match_details['skill_evidence'],api_role['skill_evidence'])
            self.assertEqual(db_role.match_details['requirements_status'],api_role['requirements_status'])
            self.assertEqual(api_role['salary_range'],'')
        detail=self.client.get(reverse('recommendation-detail',kwargs={'pk':rec.pk}))
        self.assertEqual(detail.data['top_roles'],response.data['top_roles'])
