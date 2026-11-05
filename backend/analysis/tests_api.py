
"""
Integration tests untuk REST API Feature 1 ICM.

Menggunakan mock AI agar dapat memeriksa endpoint, autentikasi,
validasi input, dan PostgreSQL tanpa memuat model berulang.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from resumes.models import Resume
from recommendations.models import JobRole
from analysis.models import JobMatch


class Feature1APITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="api_user",
            password="TestPassword123!"
        )

        self.other_user = User.objects.create_user(
            username="other_api_user",
            password="TestPassword123!"
        )

        self.resume = Resume.objects.create(
            user=self.user,
            original_filename="cv_test.pdf",
            cv_file="resumes_pdf/cv_test.pdf",
            extracted_text=(
                "Software Developer dengan pengalaman Python, "
                "Django, PostgreSQL dan REST API selama 2 tahun."
            ),
        )

        self.other_resume = Resume.objects.create(
            user=self.other_user,
            original_filename="private.pdf",
            cv_file="resumes_pdf/private.pdf",
            extracted_text="Private developer experience with Python.",
        )

        self.job_text = (
            "Membutuhkan Python, Django, PostgreSQL, "
            "REST API dan pengalaman 2 tahun."
        )

        self.mock_result = {
            "compatibility_score": Decimal("85.00"),
            "compatibility_level": "HIGH",
            "semantic_score": Decimal("80.00"),
            "skill_score": Decimal("100.00"),
            "experience_score": Decimal("75.00"),
            "education_score": Decimal("70.00"),
            "matched_skills": ["python", "django"],
            "missing_skills": ["docker"],
            "recommendations": [
                "Pelajari Docker dan terapkan pada proyek."
            ],
        }

        self.client.force_authenticate(user=self.user)

    def _post_match(self, data):
        return self.client.post(
            "/api/analysis/match/",
            data,
            format="json",
        )

    @patch("analysis.views.AnalysisService.analyze_cv_vs_job")
    def test_create_match_success(self, mock_analyze):
        mock_analyze.return_value = self.mock_result

        response = self._post_match({
            "resume_id": str(self.resume.id),
            "job_text": self.job_text,
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(JobMatch.objects.count(), 1)

        match = JobMatch.objects.get()
        self.assertEqual(match.user, self.user)
        self.assertEqual(match.resume, self.resume)
        self.assertEqual(
            match.compatibility_score,
            Decimal("85.00"),
        )

        self.assertEqual(
            response.data["data"]["compatibility"]["score"],
            85.0,
        )

        mock_analyze.assert_called_once()

    def test_unauthenticated_request_rejected(self):
        self.client.force_authenticate(user=None)

        response = self._post_match({
            "resume_id": str(self.resume.id),
            "job_text": self.job_text,
        })

        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(JobMatch.objects.count(), 0)

    def test_invalid_resume_uuid(self):
        response = self._post_match({
            "resume_id": "bukan-uuid",
            "job_text": self.job_text,
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"]["code"],
            "INVALID_RESUME_ID",
        )

    def test_cannot_analyze_other_users_resume(self):
        response = self._post_match({
            "resume_id": str(self.other_resume.id),
            "job_text": self.job_text,
        })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(JobMatch.objects.count(), 0)

    @patch("analysis.views.AnalysisService.analyze_cv_vs_job")
    def test_match_using_job_id(self, mock_analyze):
        mock_analyze.return_value = self.mock_result

        job = JobRole.objects.create(
            role_title="Backend Developer",
            category="Software Development",
            description=self.job_text,
            required_skills=["Python", "Django"],
        )

        response = self._post_match({
            "resume_id": str(self.resume.id),
            "job_id": str(job.id),
        })

        self.assertEqual(response.status_code, 201)

        match = JobMatch.objects.get()
        self.assertEqual(
            match.job_title_target,
            "Backend Developer",
        )

        self.assertEqual(
            match.job_description_text,
            self.job_text,
        )

    @patch("analysis.views.AnalysisService.analyze_cv_vs_job")
    def test_unknown_skill_score_not_saved(self, mock_analyze):
        result = self.mock_result.copy()
        result["skill_score"] = None
        mock_analyze.return_value = result

        response = self._post_match({
            "resume_id": str(self.resume.id),
            "job_text": self.job_text,
        })

        self.assertEqual(response.status_code, 422)
        self.assertEqual(JobMatch.objects.count(), 0)

    @patch("analysis.views.AnalysisService.analyze_cv_vs_job")
    def test_get_detail_and_list_matches(self, mock_analyze):
        mock_analyze.return_value = self.mock_result

        created = self._post_match({
            "resume_id": str(self.resume.id),
            "job_text": self.job_text,
        })
        self.assertEqual(created.status_code, 201)

        match_id = created.data["data"]["id"]

        detail = self.client.get(
            f"/api/analysis/match/{match_id}/"
        )

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.data["data"]["id"],
            match_id,
        )

        history = self.client.get(
            "/api/analysis/matches/"
        )

        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["data"]["count"], 1)

    @patch("analysis.views.AnalysisService.analyze_cv_vs_job")
    def test_other_user_cannot_read_match(self, mock_analyze):
        mock_analyze.return_value = self.mock_result

        created = self._post_match({
            "resume_id": str(self.resume.id),
            "job_text": self.job_text,
        })

        self.assertEqual(created.status_code, 201)

        match_id = created.data["data"]["id"]

        self.client.force_authenticate(user=self.other_user)

        detail = self.client.get(
            f"/api/analysis/match/{match_id}/"
        )

        history = self.client.get(
            "/api/analysis/matches/"
        )

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["data"]["count"], 0)

    def test_invalid_match_uuid(self):
        response = self.client.get(
            "/api/analysis/match/bukan-uuid/"
        )

        self.assertEqual(response.status_code, 400)

    def test_nonexistent_match(self):
        response = self.client.get(
            f"/api/analysis/match/{uuid.uuid4()}/"
        )

        self.assertEqual(response.status_code, 404)
