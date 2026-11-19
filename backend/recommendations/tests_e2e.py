
import io
import tempfile
from pathlib import Path
from docx import Document
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from lib import feature2 as engine
from resumes.models import Resume
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from recommendations.models import CareerRecommendation


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
            "Fresh graduate Backend Developer.\nSkills: Python, Django, Postgres, Git.\n"
            "Projects: Built RESTful APIs with Django and PostgreSQL for student scheduling.\n"
            "Summary: No experience with Docker.\nObjective: Interested in learning Kubernetes and AWS.\n"
            "Education: Bachelor in Computer Science."
        )
        temp = tempfile.TemporaryDirectory(prefix="icm-career-e2e-")
        self.addCleanup(temp.cleanup)
        temp_root = Path(temp.name).resolve()
        media = override_settings(PRIVATE_RESUME_ROOT=temp_root/"private", MEDIA_ROOT=temp_root/"legacy")
        media.enable()
        self.addCleanup(media.disable)
        client = APIClient()
        client.force_authenticate(user=user)
        document = Document()
        for line in cv_text.splitlines():
            document.add_paragraph(line)
        buffer = io.BytesIO()
        document.save(buffer)
        upload = client.post("/api/resume/upload/", {
            "cv_file": SimpleUploadedFile("synthetic-career.docx", buffer.getvalue()),
        }, format="multipart")
        self.assertEqual(upload.status_code, 201, getattr(upload, "data", upload.content))
        resume = Resume.objects.get(pk=upload.data["data"]["id"])
        prediction = engine.predict_career_categories(resume.extracted_text)
        self.assertEqual(prediction["status"], "success")

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
        self.assertEqual(probabilities, prediction["probabilities"])
        self.assertEqual([r.match_details["predicted_category"] for r in roles], prediction["predicted_categories"])
        profile = recommendation.profile_summary["cv_understanding"]
        self.assertIn("django", recommendation.detected_skills)
        self.assertNotIn("docker", recommendation.detected_skills)
        self.assertNotIn("kubernetes", recommendation.detected_skills)
        self.assertNotIn("aws", recommendation.detected_skills)
        self.assertTrue(any(item["source"] == "projects" for item in profile["skills"]))
        classifier, vectorizer = engine._load_model()
        self.assertEqual(type(classifier).__name__, "LogisticRegression")
        self.assertEqual(type(vectorizer).__name__, "TfidfVectorizer")
        self.assertEqual(len(classifier.classes_), 30)

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

        history = client.get(reverse("recommendation-list"))
        self.assertEqual(history.status_code, 200)
        rows = history.data if isinstance(history.data, list) else history.data["results"]
        self.assertEqual(rows[0]["profile_summary"], detail_response.data["profile_summary"])
        self.assertEqual(rows[0]["top_roles"], detail_response.data["top_roles"])
        for db_role, api_role in zip(roles, detail_response.data["top_roles"]):
            self.assertEqual(db_role.match_details, api_role["match_details"])
            self.assertEqual(api_role["category_probability"], probabilities[api_role["predicted_category"]])

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
