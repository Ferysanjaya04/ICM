
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


    @patch("lib.feature1.calculate_semantic_score", return_value=80.0)
    def test_real_understanding_metadata_survives_service_database_detail_and_history(self, semantic):
        cv = ("Keahlian: Python\nProyek: Built PRIVATE_EVIDENCE_MARKER using Django.\n"
              "Summary: No Docker experience. Interested in learning Kubernetes.")
        self.resume.extracted_text = cv
        self.resume.save(update_fields=["extracted_text"])
        with self.assertLogs("analysis.services", level="INFO") as logs:
            response = self._post_match({
                "resume_id": str(self.resume.pk),
                "job_text": "Python Django Docker Kubernetes. Minimum 2 years experience. Bachelor in Computer Science.",
            })
        self.assertEqual(response.status_code, 201, response.data)
        semantic.assert_called_once()
        data = response.data["data"]
        self.assertTrue({"id", "resume_id", "compatibility", "scores", "skills", "recommendations", "created_at"}.issubset(data))
        self.assertEqual(data["skills"]["matched"], ["django", "python"])
        self.assertEqual(data["skills"]["missing"], ["docker", "kubernetes"])
        self.assertEqual(data["scores"]["skill"], 50.0)
        self.assertIsNone(data["scores"]["experience"])
        self.assertIsNone(data["scores"]["education"])
        metadata = data["analysis_metadata"]
        self.assertEqual(metadata["scoring_info"]["observed_weight"], .65)
        self.assertIn("job_understanding", metadata)
        self.assertEqual(metadata["job_understanding"]["scoring_skills"], ["django", "docker", "kubernetes", "python"])
        self.assertEqual(metadata["scoring_info"]["assessment_status"], "partial")
        self.assertEqual(metadata["cv_understanding"]["engine_version"], "ai3b.1")
        for skill in metadata["cv_understanding"]["skills"]:
            self.assertEqual(skill["claim_status"], "reported_positive")
            self.assertEqual(skill["proficiency"], "unspecified")
            self.assertIn("skill_kind", skill)
            self.assertTrue(all("claim_status" in item for item in skill["evidence_items"]))
        self.assertEqual({s["name"] for s in metadata["cv_understanding"]["excluded_skill_mentions"]}, {"docker", "kubernetes"})
        self.assertTrue(any("PRIVATE_EVIDENCE_MARKER" in s["evidence"] for s in metadata["cv_understanding"]["skills"]))
        self.assertNotIn("PRIVATE_EVIDENCE_MARKER", "\n".join(logs.output))
        self.assertNotIn("No Docker experience", "\n".join(logs.output))
        match = JobMatch.objects.get(pk=data["id"])
        self.assertEqual(match.analysis_metadata, metadata)
        # Subsequent CV/parser changes must not rewrite a historical explanation.
        self.resume.extracted_text = "Skills: Docker, Kubernetes"
        self.resume.save(update_fields=["extracted_text"])
        detail = self.client.get(f"/api/analysis/match/{match.pk}/")
        history = self.client.get("/api/analysis/matches/")
        self.assertEqual(detail.data["data"]["analysis_metadata"], metadata)
        self.assertEqual(history.data["data"]["results"][0]["analysis_metadata"], metadata)

    @patch("analysis.views.AnalysisService.analyze_cv_vs_job")
    def test_undetermined_result_is_not_replaced_by_zero_or_saved(self, analyze):
        analyze.return_value = {
            "compatibility_score": None, "compatibility_level": "UNDETERMINED",
            "semantic_score": None, "skill_score": None,
            "experience_score": None, "education_score": None,
            "analysis_metadata": {"scoring_info": {"assessment_status": "undetermined", "observed_weight": 0}},
        }
        response = self._post_match({"resume_id": str(self.resume.pk), "job_text": self.job_text})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error"]["code"], "ANALYSIS_UNDETERMINED")
        self.assertEqual(response.data["error"]["details"]["scoring_info"]["assessment_status"], "undetermined")
        self.assertEqual(JobMatch.objects.count(), 0)

    def test_historical_match_without_metadata_does_not_invent_evidence(self):
        match = JobMatch.objects.create(
            user=self.user, resume=self.resume, job_description_text=self.job_text,
            compatibility_score=85, compatibility_level="HIGH", semantic_score=80, skill_score=90,
        )
        response = self.client.get(f"/api/analysis/match/{match.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["analysis_metadata"], {})


    @patch("analysis.services.analyze_cv_job", side_effect=RuntimeError("PRIVATE_EVIDENCE_MARKER"))
    def test_parser_exception_does_not_log_or_return_evidence(self, analyze):
        with self.assertLogs("analysis", level="INFO") as logs:
            response = self._post_match({"resume_id": str(self.resume.pk), "job_text": self.job_text})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("PRIVATE_EVIDENCE_MARKER", "\n".join(logs.output))
        self.assertNotIn("PRIVATE_EVIDENCE_MARKER", str(response.data))
        self.assertEqual(JobMatch.objects.count(), 0)


    @patch("lib.feature1.calculate_semantic_score", return_value=80.0)
    def test_unknown_job_skill_returns_coverage_without_fabricating_zero(self, semantic):
        response = self._post_match({
            "resume_id": str(self.resume.pk),
            "job_text": "Collaborate with colleagues to produce reliable outcomes for customers.",
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error"]["code"], "JOB_SKILLS_UNDETERMINED")
        info = response.data["error"]["details"]["scoring_info"]
        self.assertIn("skill", info["unknown_components"])
        self.assertIsNone(info["effective_weights"]["skill"])
        self.assertEqual(JobMatch.objects.count(), 0)


    @patch("lib.feature1.calculate_semantic_score", return_value=80.0)
    def test_structured_job_requirements_and_unknowns_survive_history(self, semantic):
        self.resume.extracted_text = 'Skills: Python\nInternship\nJunior Data Engineer September 2025 - Desember 2025\nCertifications\nBachelor level Python course.'
        self.resume.save(update_fields=['extracted_text'])
        response=self._post_match({'resume_id':str(self.resume.pk), 'job_text':'Required skills: Python\nPreferred skills: Docker\nResponsibilities: Maintain Kubernetes services.\nRequirements: Minimum 1 year professional experience. Bachelor in Computer Science required.'})
        self.assertEqual(response.status_code,201,response.data)
        data=response.data['data'];metadata=data['analysis_metadata']
        self.assertEqual(data['scores']['skill'],100)
        self.assertIsNone(data['scores']['experience'])
        self.assertIsNone(data['scores']['education'])
        self.assertEqual(metadata['job_understanding']['required_skills'],['python'])
        self.assertEqual(metadata['job_understanding']['preferred_skills'],['docker'])
        self.assertEqual(metadata['job_understanding']['responsibility_skills'],['kubernetes'])
        self.assertEqual(metadata['experience']['assessment_status'],'unknown')
        self.assertEqual(metadata['scoring_info']['observed_weight'],.65)
        saved=JobMatch.objects.get(pk=data['id'])
        self.assertEqual(saved.analysis_metadata,metadata)
        detail=self.client.get(f'/api/analysis/match/{saved.pk}/')
        history=self.client.get('/api/analysis/matches/')
        self.assertEqual(detail.data['data']['analysis_metadata'],metadata)
        self.assertEqual(history.data['data']['results'][0]['analysis_metadata'],metadata)
