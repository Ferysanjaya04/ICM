
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


from django.test import SimpleTestCase
import tempfile
from pathlib import Path
from resumes import extraction as quality_extraction


class ExtractionQualityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from lib.evaluate_cv_baseline import create_evaluation_documents
        cls.temp=tempfile.TemporaryDirectory(prefix='icm-quality-tests-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.documents=create_evaluation_documents(Path(cls.temp.name))

    def upload(self, data, name='fixture.pdf'):
        return SimpleUploadedFile(name,data)

    def test_two_column_order_with_review_warning_and_no_ocr(self):
        name,data,gold=self.documents[0]
        with mock.patch.object(quality_extraction,'_ocr_pdf_page',side_effect=AssertionError('Digital page must not OCR')):
            result=quality_extraction.extract_document(self.upload(data,name))
        self.assertLess(result['text'].index('Used Python'),result['text'].index('Summary:'))
        self.assertEqual(result['quality']['pages'][0]['reading_order'],'two_column_blocks')
        self.assertEqual(result['quality']['ocr_pages'],[])
        self.assertIsNone(result['quality']['pages'][0]['ocr_confidence'])
        self.assertEqual(result['quality']['status'],'needs_review')

    def test_single_column_native_text_remains_native(self):
        import pymupdf as fitz
        doc=fitz.open();page=doc.new_page()
        text='Skills: Python, SQL, SOL\nProjects: Used Python and PostgreSQL in a campus project.'
        page.insert_text((40,60),text);data=doc.tobytes()
        expected=quality_extraction._normalize_text(page.get_text('text',sort=True));doc.close()
        result=quality_extraction.extract_document(self.upload(data))
        self.assertEqual(result['text'],expected)
        self.assertIn('SOL',result['text'])
        self.assertEqual(result['quality']['status'],'text_extracted')
        self.assertEqual(result['quality']['ocr_pages'],[])

    @skipIf(not HAS_OCR,'Tesseract unavailable')
    def test_real_scan_bilingual_retains_sql_without_false_skills(self):
        name,data,gold=self.documents[1]
        result=quality_extraction.extract_document(self.upload(data,name))
        self.assertIn('SQL',result['text'])
        page=result['quality']['pages'][0]
        self.assertEqual(page['method'],'ocr')
        self.assertEqual(page['ocr_language'],'ind+eng')
        self.assertIsNotNone(page['ocr_confidence'])
        self.assertIn('not accuracy probability',page['ocr_confidence']['scale'])
        from lib.cv_understanding import understand_cv_from_file
        skills={x['name'] for x in understand_cv_from_file(result['text'])['skills']}
        self.assertIn('sql',skills)
        self.assertNotIn('docker',skills)
        self.assertNotIn('kubernetes',skills)

    def test_sol_is_not_rewritten_when_ocr_remains_ambiguous(self):
        data={'text':['Skills:','Python','SOL'],'conf':[95,95,40],
              'block_num':[1,1,1],'par_num':[1,1,1],'line_num':[1,1,1]}
        with mock.patch.object(quality_extraction.pytesseract,'image_to_data',return_value=data):
            result=quality_extraction._ocr_image_result(None,quality_extraction.pytesseract,20)
        self.assertEqual(result['text'],'Skills: Python SOL')
        self.assertIn('ambiguous_technical_token_not_corrected',result['warnings'])
        self.assertEqual(result['confidence']['min_word_score'],40)

    def test_partial_ocr_failure_is_metadata_not_invented_text(self):
        import pymupdf as fitz
        doc=fitz.open(stream=self.documents[0][1],filetype='pdf')
        other=fitz.open(stream=self.documents[1][1],filetype='pdf');doc.insert_pdf(other)
        data=doc.tobytes();doc.close();other.close()
        with mock.patch.object(quality_extraction,'_ocr_pdf_page',side_effect=RuntimeError('private/path MUST NOT LEAK')):
            result=quality_extraction.extract_document(self.upload(data))
        self.assertEqual(result['quality']['status'],'partial')
        self.assertEqual(result['quality']['failed_pages'],[2])
        self.assertEqual(result['quality']['ocr_failed_pages'],[2])
        self.assertEqual(result['quality']['pages'][1]['method'],'failed')
        self.assertIsNone(result['quality']['pages'][1]['ocr_confidence'])
        self.assertNotIn('MUST NOT LEAK',str(result))

    def test_table_structure_and_public_text_wrapper_compatible(self):
        name,data,gold=self.documents[2]
        result=quality_extraction.extract_document(self.upload(data,name))
        self.assertEqual(result['quality']['structure']['table_count'],1)
        self.assertIsNone(result['quality']['page_count'])
        self.assertLess(result['text'].index('Skills:'),result['text'].index('Projects:'))
        self.assertEqual(quality_extraction.extract_text_from_file(self.upload(data,name)),result['text'])

    def test_unavailable_and_exhausted_ocr_have_explicit_quality(self):
        name,data,gold=self.documents[0]
        with mock.patch.object(quality_extraction,'MIN_PAGE_TEXT_CHARS',10000),mock.patch.object(quality_extraction,'MAX_OCR_PAGES',0):
            result=quality_extraction.extract_document(self.upload(data,name))
        self.assertEqual(result['quality']['pages'][0]['ocr_status'],'skipped_budget')
        self.assertIn(1,result['quality']['low_text_pages'])
        with mock.patch.object(quality_extraction,'MIN_PAGE_TEXT_CHARS',10000),mock.patch.object(quality_extraction,'_get_tesseract',return_value=None):
            result=quality_extraction.extract_document(self.upload(data,name))
        self.assertEqual(result['quality']['pages'][0]['ocr_status'],'unavailable')

    def test_damaged_docx_empty_and_corrupt_pdf_fail_safely(self):
        for name,data in [('empty.pdf',b''),('bad.pdf',b'%PDF-damaged'),('bad.docx',b'PKdamaged')]:
            with self.subTest(name=name),self.assertRaises(ValueError):
                quality_extraction.extract_document(self.upload(data,name))

    def test_complex_layout_falls_back_with_warning(self):
        class Page:
            class Rect:
                x0=0;x1=800;width=800
            rect=Rect()
            def get_text(self,kind,sort):
                if kind=='text':return 'Native fallback text'
                return [(30,y,260,y+15,'Left',0,0) for y in [60,100,140]]+[(430,y,650,y+15,'Right',0,0) for y in [60,100,140]]+[(30,110,760,130,'Spanning body text',0,0)]
        text,order,warnings=quality_extraction._native_page_text(Page())
        self.assertEqual(text,'Native fallback text')
        self.assertIn('reading_order_uncertain',warnings)


    def test_narrow_label_column_is_not_reordered_as_document_columns(self):
        class Page:
            class Rect:
                x0=0;x1=800;width=800
            rect=Rect()
            def get_text(self,kind,sort):
                if kind=='text':return 'Original row-wise table content'
                return [(30,y,180,y+15,'Category:',0,0) for y in [60,100,140]]+[(430,y,650,y+15,'Python Django PostgreSQL Git',0,0) for y in [60,100,140]]
        text,order,warnings=quality_extraction._native_page_text(Page())
        self.assertEqual(text,'Original row-wise table content')
        self.assertIn('reading_order_uncertain',warnings)

    def test_ocr_missing_confidence_is_null_and_language_fallback_bounded(self):
        data={'text':['Skills:','SOL'],'conf':[-1,-1],
              'block_num':[1,1],'par_num':[1,1],'line_num':[1,1]}
        with mock.patch.object(quality_extraction.pytesseract,'image_to_data',side_effect=[RuntimeError('failed loading language data'),data]) as run:
            result=quality_extraction._ocr_image_result(None,quality_extraction.pytesseract,20)
        self.assertIsNone(result['confidence'])
        self.assertEqual(result['language'],'eng')
        self.assertIn('ocr_language_fallback',result['warnings'])
        self.assertLessEqual(run.call_args.kwargs['timeout'],20)
