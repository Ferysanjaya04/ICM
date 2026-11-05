
"""
ICM - Feature 1 End-to-End Integration Test.

Alur:
1. Autentikasi pengguna
2. Upload PDF melalui REST API
3. Ekstraksi teks PDF
4. Analisis menggunakan SentenceTransformer asli
5. Simpan JobMatch ke database
6. Ambil detail dan riwayat analisis

Tidak menggunakan mock AI.
Tidak menggunakan CV atau data pribadi sungguhan.
"""

import io
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from rest_framework.test import APIClient

from django.core.files.uploadedfile import SimpleUploadedFile

from reportlab.pdfgen import canvas

from resumes.models import Resume
from analysis.models import JobMatch


class Feature1EndToEndTests(TestCase):
    """
    Pengujian alur lengkap Feature 1 menggunakan REST API
    dan model SentenceTransformer yang sebenarnya.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.temp_media = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.temp_media.name
        )
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        cls.temp_media.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="e2e_feature1_user",
            email="e2e@example.com",
            password="TestPassword123!",
        )

        self.client.force_authenticate(user=self.user)

        self.cv_text = [
            "CURRICULUM VITAE",
            "Nama: Andi Pratama",
            "Posisi: Backend Developer",
            "Pendidikan: S1 Teknik Informatika",
            "Keahlian: Python, Django, PostgreSQL, Docker, REST API",
            "Pengalaman kerja: 2 tahun pengalaman sebagai Backend Developer",
            "Membangun REST API menggunakan Python dan Django.",
            "Mengelola PostgreSQL dan deployment aplikasi dengan Docker.",
        ]

        self.job_text = (
            "Lowongan Backend Developer. "
            "Membutuhkan Python, Django, PostgreSQL, Docker, "
            "dan REST API untuk pengembangan aplikasi backend. "
            "Minimal 2 tahun pengalaman kerja. "
            "Pendidikan minimal S1 Teknik Informatika."
        )

    def create_test_pdf(self):
        """
        Membuat PDF digital yang benar-benar memiliki
        konten teks dan dapat diekstrak.
        """
        buffer = io.BytesIO()

        pdf = canvas.Canvas(buffer)

        y = 780

        for line in self.cv_text:
            pdf.drawString(50, y, line)
            y -= 25

        pdf.save()
        buffer.seek(0)

        return SimpleUploadedFile(
            name="cv_andi_pratama.pdf",
            content=buffer.getvalue(),
            content_type="application/pdf",
        )

    def test_full_cv_to_ai_to_database_pipeline(self):
        """
        Menguji seluruh pipeline tanpa mock AI.
        """

        # ============================================
        # STEP 1: Upload CV PDF
        # ============================================

        pdf_file = self.create_test_pdf()

        upload_response = self.client.post(
            "/api/resume/upload/",
            {"cv_file": pdf_file},
            format="multipart",
        )

        # ResumeUploadView mungkin menggunakan field
        # "cv_file", bukan "file".
        # Jika test gagal di sini, periksa nama field
        # pada resumes/views.py.
        self.assertEqual(
            upload_response.status_code,
            201,
            f"Upload gagal: {upload_response.data}",
        )

        # Pastikan Resume benar-benar disimpan.
        self.assertEqual(
            Resume.objects.filter(user=self.user).count(),
            1,
        )

        resume = Resume.objects.get(user=self.user)

        self.assertTrue(resume.extracted_text.strip())

        self.assertIn(
            "Python",
            resume.extracted_text,
        )

        self.assertIn(
            "Django",
            resume.extracted_text,
        )

        # ============================================
        # STEP 2: Jalankan AI melalui REST API
        # ============================================

        analysis_response = self.client.post(
            "/api/analysis/match/",
            {
                "resume_id": str(resume.id),
                "job_text": self.job_text,
            },
            format="json",
        )

        self.assertEqual(
            analysis_response.status_code,
            201,
            f"Analisis gagal: {analysis_response.data}",
        )

        self.assertEqual(
            analysis_response.data["status"],
            "success",
        )

        result = analysis_response.data["data"]

        # ============================================
        # STEP 3: Periksa hasil AI
        # ============================================

        self.assertIn("compatibility", result)
        self.assertIn("scores", result)
        self.assertIn("skills", result)
        self.assertIn("recommendations", result)

        compatibility = result["compatibility"]

        self.assertIsNotNone(
            compatibility["score"]
        )

        self.assertGreaterEqual(
            compatibility["score"],
            0,
        )

        self.assertLessEqual(
            compatibility["score"],
            100,
        )

        self.assertIn(
            compatibility["level"],
            ("LOW", "MEDIUM", "HIGH"),
        )

        self.assertIsNotNone(
            result["scores"]["semantic"]
        )

        self.assertIsNotNone(
            result["scores"]["skill"]
        )

        self.assertIn(
            "python",
            [skill.lower() for skill in result["skills"]["matched"]],
        )

        # ============================================
        # STEP 4: Verifikasi database
        # ============================================

        self.assertEqual(
            JobMatch.objects.filter(user=self.user).count(),
            1,
        )

        job_match = JobMatch.objects.get(user=self.user)

        self.assertEqual(
            job_match.resume_id,
            resume.id,
        )

        self.assertEqual(
            float(job_match.compatibility_score),
            compatibility["score"],
        )

        # ============================================
        # STEP 5: GET detail analisis
        # ============================================

        detail_response = self.client.get(
            f"/api/analysis/match/{job_match.id}/"
        )

        self.assertEqual(
            detail_response.status_code,
            200,
        )

        self.assertEqual(
            detail_response.data["data"]["id"],
            str(job_match.id),
        )

        # ============================================
        # STEP 6: GET riwayat analisis
        # ============================================

        history_response = self.client.get(
            "/api/analysis/matches/"
        )

        self.assertEqual(
            history_response.status_code,
            200,
        )

        self.assertEqual(
            history_response.data["data"]["count"],
            1,
        )
