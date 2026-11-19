"""Access and storage regressions using synthetic documents and temporary roots."""

import io
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from docx import Document
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import Resume
from .storage import PrivateResumeStorage


CV_TEXT = (
    "Backend Developer with 3 years of experience. Skills: Python, Django, "
    "PostgreSQL, Docker, Git, REST API. Education: Bachelor in Computer Science."
)


class ResumeSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="private_owner")
        cls.other = User.objects.create_user(username="private_other")

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="icm-security-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.private = self.root / "private"
        self.legacy = self.root / "legacy"
        override = override_settings(
            PRIVATE_RESUME_ROOT=self.private, MEDIA_ROOT=self.legacy,
        )
        override.enable()
        self.addCleanup(override.disable)
        self.client = APIClient()
        self.login(self.owner)

    def login(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")

    def upload(self):
        buffer = io.BytesIO()
        doc = Document()
        doc.add_paragraph(CV_TEXT)
        doc.save(buffer)
        response = self.client.post(
            reverse("resume-upload"),
            {"cv_file": SimpleUploadedFile("synthetic.docx", buffer.getvalue())},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(response.data), {"status", "data"})
        self.assertEqual(set(response.data["data"]), {
            "id", "original_filename", "extracted_text", "uploaded_at", "extraction_quality",
        })
        quality = response.data['data']['extraction_quality']
        self.assertEqual(quality['schema_version'], 'ai4a.1')
        self.assertNotIn(str(self.private), str(quality))
        resume = Resume.objects.get(pk=response.data["data"]["id"])
        return resume, buffer.getvalue()

    def document(self, name="resumes_pdf/old.pdf", payload=b"%PDF-synthetic-legacy"):
        path = self.legacy / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return Resume.objects.create(
            user=self.owner, original_filename="old.pdf", cv_file=name,
            extracted_text=CV_TEXT,
        )

    def download(self, resume):
        return self.client.get(reverse("resume-download", args=[resume.pk]))

    def test_owner_uploads_to_private_root_and_downloads_exact_file(self):
        resume, payload = self.upload()
        self.assertIsInstance(resume.cv_file.storage, PrivateResumeStorage)
        self.assertTrue(Path(resume.cv_file.path).is_relative_to(self.private))
        self.assertFalse(self.legacy.exists())
        self.assertEqual(resume.cv_file.size, len(payload))
        response = self.download(resume)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(b"".join(response.streaming_content), payload)
        self.assertTrue(response.closed)

    def test_windows_short_root_alias_returns_safe_relative_file_keys(self):
        if os.name != "nt":
            self.skipTest("Windows 8.3 path regression")
        import ctypes

        self.private.mkdir()
        short_path = ctypes.windll.kernel32.GetShortPathNameW
        short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        short_path.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32768)
        length = short_path(str(self.private), buffer, len(buffer))
        if not length or os.path.normcase(buffer.value) == os.path.normcase(str(self.private)):
            self.skipTest("Temporary filesystem does not provide a distinct Windows 8.3 alias")

        with override_settings(PRIVATE_RESUME_ROOT=buffer.value):
            store = PrivateResumeStorage()
            first = store.save("resumes_pdf/synthetic.pdf", ContentFile(b"first"))
            second = store.save("resumes_pdf/synthetic.pdf", ContentFile(b"second"))
            self.assertNotEqual(first, second)
            for name, expected in ((first, b"first"), (second, b"second")):
                self.assertFalse(Path(name).is_absolute())
                self.assertNotIn("..", name.replace("\\", "/").split("/"))
                self.assertTrue(Path(store.path(name)).is_relative_to(self.private.resolve()))
                with store.open(name) as document:
                    self.assertEqual(document.read(), expected)

    def test_other_user_cannot_download_or_list_owner_document(self):
        resume = self.document()
        self.login(self.other)
        with patch.object(resume.cv_file.storage, "open") as opened:
            self.assertEqual(self.download(resume).status_code, 404)
            opened.assert_not_called()
        response = self.client.get(reverse("resume-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["resumes"], [])

    def test_anonymous_cannot_download_upload_or_list(self):
        resume = self.document()
        self.client.credentials()
        self.assertEqual(self.download(resume).status_code, 401)
        self.assertEqual(self.client.get(reverse("resume-list")).status_code, 401)
        self.assertEqual(self.client.post(reverse("resume-upload"), {}).status_code, 401)

    def test_invalid_token_cannot_download(self):
        resume = self.document()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        self.assertEqual(self.download(resume).status_code, 401)

    def test_public_media_and_static_urls_do_not_serve_new_or_legacy_files(self):
        new, _ = self.upload()
        old = self.document()
        for debug in (True, False):
            for user in (self.owner, self.other, None):
                if user:
                    self.login(user)
                else:
                    self.client.credentials()
                with override_settings(DEBUG=debug):
                    for resume in (new, old):
                        for prefix in ("/media/", "/static/", "/private/"):
                            with self.subTest(debug=debug, user=bool(user), prefix=prefix):
                                self.assertEqual(
                                    self.client.get(prefix + resume.cv_file.name).status_code, 404,
                                )

    def test_storage_cannot_generate_public_url(self):
        resume = self.document()
        with self.assertRaises(ValueError):
            _ = resume.cv_file.url

    def test_attachment_filename_does_not_expose_path_or_allow_header_injection(self):
        resume = self.document()
        resume.original_filename = "..\\secret-folder\\synthetic\r\n.pdf"
        resume.save(update_fields=["original_filename"])
        response = self.download(resume)
        self.assertEqual(response.status_code, 200)
        self.assertIn('filename="synthetic.pdf"', response["Content-Disposition"])
        self.assertNotIn("secret-folder", response["Content-Disposition"])
        b"".join(response.streaming_content)
        self.assertTrue(response.closed)

    def test_production_https_redirect_and_https_owner_download(self):
        resume = self.document()
        with override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=None):
            url = reverse("resume-download", args=[resume.pk])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 301)
            self.assertTrue(response["Location"].startswith("https://"))
            response = self.client.get(url, secure=True)
            self.assertEqual(response.status_code, 200)
            b"".join(response.streaming_content)
            self.assertTrue(response.closed)
            self.login(self.other)
            self.assertEqual(self.client.get(url, secure=True).status_code, 404)
            self.client.credentials()
            self.assertEqual(self.client.get(url, secure=True).status_code, 401)

    def test_owner_reads_legacy_without_copying_moving_or_deleting(self):
        resume = self.document()
        self.assertEqual(Path(resume.cv_file.path), self.legacy / resume.cv_file.name)
        response = self.download(resume)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-synthetic-legacy")
        self.assertTrue(response.closed)
        self.assertTrue((self.legacy / resume.cv_file.name).exists())
        self.assertFalse(self.private.exists())

    def test_django_file_can_be_closed_and_reopened_for_new_and_legacy_documents(self):
        new, uploaded = self.upload()
        old = self.document()
        for resume, expected in ((new, uploaded), (old, b"%PDF-synthetic-legacy")):
            for _ in range(2):
                with resume.cv_file.open("rb") as document:
                    self.assertEqual(document.read(), expected)

    def test_legacy_name_collision_preserves_old_content_and_writes_new_privately(self):
        resume = self.document()
        saved = resume.cv_file.storage.save(resume.cv_file.name, ContentFile(b"new-private"))
        self.assertNotEqual(saved, resume.cv_file.name)
        self.assertEqual((self.private / saved).read_bytes(), b"new-private")
        self.assertEqual((self.legacy / resume.cv_file.name).read_bytes(), b"%PDF-synthetic-legacy")

    def test_no_legacy_write_mode_or_implicit_delete(self):
        resume = self.document()
        with self.assertRaises(ValueError):
            resume.cv_file.storage.open(resume.cv_file.name, "wb")
        with self.assertRaises(NotImplementedError):
            resume.cv_file.storage.delete(resume.cv_file.name)
        self.assertEqual((self.legacy / resume.cv_file.name).read_bytes(), b"%PDF-synthetic-legacy")

    def test_missing_unknown_ownerless_or_invalid_id_returns_404(self):
        resume = self.document()
        (self.legacy / resume.cv_file.name).unlink()  # synthetic temp fixture only
        self.assertEqual(self.download(resume).status_code, 404)
        self.assertEqual(self.client.get(reverse("resume-download", args=[uuid.uuid4()])).status_code, 404)
        self.assertEqual(self.client.get("/api/resume/not-a-uuid/download/").status_code, 404)
        resume.user = None
        resume.save(update_fields=["user"])
        self.assertEqual(self.download(resume).status_code, 404)

    def test_storage_rejects_posix_windows_and_ads_traversal(self):
        store = PrivateResumeStorage()
        outside = self.root / "outside.pdf"
        outside.write_bytes(b"not-a-resume")
        names = [
            "../outside.pdf", "resumes_pdf/../../outside.pdf", str(outside),
            "/etc/passwd", "C:/outside.pdf", "C:outside.pdf", "\\\\server\\share\\file",
            "..\\outside.pdf", "resumes_pdf\\..\\outside.pdf", "resumes_pdf/x:stream",
            "resumes_pdf/./x", "resumes_pdf//x", "resumes_pdf/\x00x",
        ]
        for name in names:
            with self.subTest(name=name):
                with self.assertRaises(SuspiciousFileOperation):
                    store.open(name)
                with self.assertRaises(SuspiciousFileOperation):
                    store.save(name, ContentFile(b"blocked"))
        self.assertEqual(outside.read_bytes(), b"not-a-resume")

    def test_tampered_database_file_path_returns_404_without_path_disclosure(self):
        resume = self.document()
        resume.cv_file.name = "../outside.pdf"
        resume.save(update_fields=["cv_file"])
        response = self.download(resume)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("outside.pdf", str(response.data))
        self.assertNotIn(str(self.root), str(response.data))

    def test_symlink_escape_is_rejected_in_private_and_legacy_storage(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "synthetic.pdf").write_bytes(b"outside-content")
        for base in (self.private, self.legacy):
            base.mkdir()
            try:
                os.symlink(outside, base / "link", target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"Host cannot create synthetic symlink: {type(exc).__name__}")
        store = PrivateResumeStorage()
        with self.assertRaises(SuspiciousFileOperation):
            store.open("link/synthetic.pdf")
        with self.assertRaises(SuspiciousFileOperation):
            store.save("link/new.pdf", ContentFile(b"blocked"))
        self.assertFalse((outside / "new.pdf").exists())

    def test_stored_legacy_cv_still_flows_through_both_ai_apis(self):
        # Real model execution is also covered by the unchanged Feature 1/2 E2E suites.
        from recommendations.tests_api import fake_ai_result
        resume = self.document()
        with resume.cv_file.open("rb") as document:
            self.assertEqual(document.read(), b"%PDF-synthetic-legacy")
        with patch("analysis.views.AnalysisService.analyze_cv_vs_job") as analyze:
            analyze.return_value = {
                "compatibility_score": 80, "compatibility_level": "HIGH",
                "semantic_score": 80, "skill_score": 80,
                "experience_score": None, "education_score": None,
                "matched_skills": ["python"], "missing_skills": [], "recommendations": [],
            }
            response = self.client.post(reverse("analysis:analyze"), {
                "resume_id": str(resume.pk), "job_text": "Backend role requiring Python and Django.",
            }, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(analyze.call_args.kwargs["cv_text"], CV_TEXT)
        with patch("recommendations.views.recommend_career", return_value=fake_ai_result()) as recommend:
            response = self.client.post(reverse("recommendation-generate"), {
                "resume_id": str(resume.pk),
            }, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            recommend.assert_called_once_with(CV_TEXT)
        self.login(self.other)
        for endpoint, data in (
            ("analysis:analyze", {"resume_id": str(resume.pk), "job_text": "Python Django backend role"}),
            ("recommendation-generate", {"resume_id": str(resume.pk)}),
        ):
            self.assertEqual(self.client.post(reverse(endpoint), data, format="json").status_code, 404)
