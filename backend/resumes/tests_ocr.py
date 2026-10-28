
"""
TEST SUITE: OCR FALLBACK & PDF EXTRACTION
==========================================

Tests untuk memverifikasi implementasi Issue #34 M6-AI:
1. PyMuPDF extraction untuk PDF digital
2. OCR fallback untuk PDF scan/gambar
3. Normalisasi dan preprocessing

CATATAN: Tests yang menggunakan PDF scan sungguhan dan Tesseract executable
hanya bisa dijalankan setelah Tesseract OCR diinstall di sistem.

Tests dengan mock pytesseract bisa dijalankan tanpa Tesseract executable.
"""

import io
from unittest import skipIf, mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from resumes.models import Resume
from resumes.extraction import (
    extract_text_from_file,
    HAS_OCR,
)


if HAS_OCR:
    import pytesseract


class PDFExtractionTests(TestCase):
    """Test PyMuPDF extraction untuk PDF digital."""

    def setUp(self):
        username = f"user_pdf_extraction_{id(self)}"
        self.user = User.objects.create_user(
            username=username,
            email="test@example.com",
            password="testpass123",
        )

    def test_extract_text_from_digital_pdf(self):
        """PDF digital berhasil diekstrak tanpa OCR."""
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF not available")

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 50),
            "Test CV\nSkills: Python, Django\nExperience: 5 years",
        )

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        pdf_file = SimpleUploadedFile(
            "test.pdf",
            pdf_bytes.getvalue(),
            content_type="application/pdf",
        )

        extracted = extract_text_from_file(pdf_file)

        self.assertIn("Test CV", extracted)
        self.assertIn("Python", extracted)
        self.assertIn("Django", extracted)

    def test_pdf_with_no_text_triggers_ocr_preparation(self):
        """PDF kosong menghasilkan error informatif."""
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF not available")

        doc = fitz.open()
        doc.new_page()

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        pdf_file = SimpleUploadedFile(
            "scan.pdf",
            pdf_bytes.getvalue(),
            content_type="application/pdf",
        )

        with self.assertRaises(ValueError) as ctx:
            extract_text_from_file(pdf_file)

        error_msg = str(ctx.exception).lower()
        self.assertTrue(
            any(word in error_msg for word in ("ocr", "teks", "text")),
            f"Error message should mention OCR or missing text: {ctx.exception}",
        )

    def test_corrupted_pdf_error_handling(self):
        """PDF rusak ditangani dengan error yang jelas."""
        pdf_file = SimpleUploadedFile(
            "corrupted.pdf",
            b"PDF corrupted data %%%%%",
            content_type="application/pdf",
        )

        with self.assertRaises(ValueError) as ctx:
            extract_text_from_file(pdf_file)

        self.assertIn("rusak", str(ctx.exception).lower())


@skipIf(
    not HAS_OCR,
    "OCR not available - Tesseract executable not accessible in this environment",
)
class OCRFallbackTests(TestCase):
    """Test OCR fallback untuk PDF scan."""

    def setUp(self):
        username = f"user_ocr_fallback_{id(self)}"
        self.user = User.objects.create_user(
            username=username,
            email="test@example.com",
            password="testpass123",
        )

    def test_ocr_fallback_for_scanned_pdf(self):
        """PDF berisi gambar diproses menggunakan OCR."""
        try:
            import fitz
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Required packages not available")

        doc = fitz.open()
        page = doc.new_page()

        img = Image.new("RGB", (600, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "Python Developer", fill="black")

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        page.insert_image(page.rect, stream=img_bytes.getvalue())

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        pdf_file = SimpleUploadedFile(
            "scan.pdf",
            pdf_bytes.getvalue(),
            content_type="application/pdf",
        )

        extracted = extract_text_from_file(pdf_file)

        self.assertIsNotNone(extracted)
        self.assertGreater(len(extracted.strip()), 0)

    
    def test_ocr_language_fallback_ind_to_eng(self):
        """OCR beralih ke bahasa Inggris jika bahasa Indonesia gagal."""
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF not available")

        with mock.patch(
            "resumes.extraction.pytesseract.image_to_string"
        ) as mock_ocr:
            mock_ocr.side_effect = [
                Exception("Language not found"),
                "Python Django",
            ]

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), "Test OCR")

            pdf_bytes = io.BytesIO()
            doc.save(pdf_bytes)
            doc.close()

            pdf_file = SimpleUploadedFile(
                "fallback_test.pdf",
                pdf_bytes.getvalue(),
                content_type="application/pdf",
            )

            from resumes.extraction import _extract_text_with_ocr

            extracted = _extract_text_with_ocr(pdf_file)

            self.assertEqual(extracted, "Python Django")
            self.assertEqual(mock_ocr.call_count, 2)
            self.assertEqual(
                mock_ocr.call_args_list[0].kwargs["lang"], "ind"
            )
            self.assertEqual(
                mock_ocr.call_args_list[1].kwargs["lang"], "eng"
            )


class OCRIntegrationTests(APITestCase):
    """Test OCR integration dengan upload flow."""

    def setUp(self):
        username = f"user_ocr_integration_{id(self)}"
        self.user = User.objects.create_user(
            username=username,
            email="test@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_upload_digital_pdf_stored_in_db(self):
        """PDF digital diupload dan teksnya disimpan ke database."""
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF not available")

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 50),
            "John Doe\nPython Developer\n5 years experience",
        )

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        pdf_file = SimpleUploadedFile(
            "john_doe_cv.pdf",
            pdf_bytes.getvalue(),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/resume/upload/",
            {"cv_file": pdf_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resume = Resume.objects.filter(user=self.user).first()
        self.assertIsNotNone(resume)
        self.assertIn("John Doe", resume.extracted_text)
        self.assertIn("Python", resume.extracted_text)

    @skipIf(
        not HAS_OCR,
        "OCR not available - Tesseract executable not accessible in this environment",
    )
    def test_upload_scanned_pdf_with_ocr(self):
        """Placeholder untuk pengujian upload PDF scan."""
        self.skipTest("Implementasi pengujian upload PDF scan belum tersedia")


class NormalizationIntegrationTests(APITestCase):
    """Test integrasi normalisasi teks dengan Feature 1 & 2."""

    def setUp(self):
        username = f"user_normalization_{id(self)}"
        self.user = User.objects.create_user(
            username=username,
            email="test@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_extracted_text_passed_to_feature1(self):
        """Teks hasil ekstraksi dapat diproses oleh Feature 1."""
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF not available")

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 50),
            "Senior Python Developer\nSkills: Python, Django, PostgreSQL",
        )

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        pdf_file = SimpleUploadedFile(
            "cv.pdf",
            pdf_bytes.getvalue(),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/resume/upload/",
            {"cv_file": pdf_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resume = Resume.objects.filter(user=self.user).first()
        self.assertIsNotNone(resume)

        from lib.feature1 import normalize_text

        normalized = normalize_text(resume.extracted_text)

        self.assertIsNotNone(normalized)
        self.assertGreater(len(normalized), 0)
