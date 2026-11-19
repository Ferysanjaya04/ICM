
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
from pathlib import Path, PureWindowsPath

from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.response import Response

from rest_framework.test import APIClient

from django.core.files.uploadedfile import SimpleUploadedFile

from reportlab.pdfgen import canvas

from resumes.models import Resume
from analysis.models import JobMatch


def response_body(response):
    """Keep assertion failures useful for DRF responses and middleware errors alike."""
    if hasattr(response, "data"):
        return str(response.data)[:2000]
    return response.content.decode(response.charset or "utf-8", errors="replace")[:2000]


class ResponseDiagnosticTests(SimpleTestCase):
    def test_upload_failure_diagnostics_accept_drf_and_plain_http_responses(self):
        for response, expected in (
            (Response({"error": "synthetic extraction failure"}, status=400), "synthetic extraction failure"),
            (HttpResponseBadRequest(b"synthetic traversal rejection"), "synthetic traversal rejection"),
            (Response(None, status=400), "None"),
        ):
            with self.subTest(response_type=type(response).__name__):
                self.assertIn(expected, response_body(response))


class Feature1EndToEndTests(TestCase):
    """
    Pengujian alur lengkap Feature 1 menggunakan REST API
    dan model SentenceTransformer yang sebenarnya.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.temp_media = tempfile.TemporaryDirectory()
        temp_root = Path(cls.temp_media.name).resolve()
        cls.private_media_root = temp_root / "private"
        cls.legacy_media_root = temp_root / "legacy"
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.legacy_media_root,
            PRIVATE_RESUME_ROOT=cls.private_media_root,
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
            f"Upload gagal: {response_body(upload_response)}",
        )

        # Pastikan Resume benar-benar disimpan.
        self.assertEqual(
            Resume.objects.filter(user=self.user).count(),
            1,
        )

        resume = Resume.objects.get(user=self.user)

        # FileField must store a relative key, never a canonical/temporary path.
        stored_name = resume.cv_file.name.replace("\\", "/")
        self.assertFalse(PureWindowsPath(stored_name).drive)
        self.assertFalse(stored_name.startswith("/"))
        self.assertNotIn("..", stored_name.split("/"))
        self.assertTrue(Path(resume.cv_file.path).is_relative_to(self.private_media_root))
        self.assertFalse((self.legacy_media_root / stored_name).exists())

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
            f"Analisis gagal: {response_body(analysis_response)}",
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
        self.assertEqual(result["analysis_metadata"]["semantic_model"], "all-MiniLM-L6-v2")
        evidence = result["analysis_metadata"]["cv_understanding"]["skills"]
        self.assertTrue(any(skill["name"] == "python" and skill["evidence"] for skill in evidence))
        self.assertEqual(result["analysis_metadata"]["scoring_info"]["base_weights"],
                         {"semantic": .25, "skill": .40, "experience": .20, "education": .15})

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
        self.assertEqual(job_match.analysis_metadata, result["analysis_metadata"])

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


class MultiFormatOriginalModelsE2ETests(TestCase):
    """Backend integrity checks, separate from accuracy of extracted evidence."""

    def setUp(self):
        from lib.evaluate_cv_baseline import create_evaluation_documents
        self.temporary = tempfile.TemporaryDirectory(prefix='icm-ai3e-e2e-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        media = override_settings(PRIVATE_RESUME_ROOT=self.root/'private', MEDIA_ROOT=self.root/'legacy')
        media.enable();self.addCleanup(media.disable)
        self.documents = create_evaluation_documents(self.root/'fixtures')
        self.owner = User.objects.create_user(username='ai3e_owner', password='SyntheticPassword123!')
        self.other = User.objects.create_user(username='ai3e_other', password='SyntheticPassword123!')
        self.api = APIClient();self.api.force_authenticate(self.owner)

    def test_three_formats_through_both_original_models_database_and_history(self):
        from django.urls import reverse
        from recommendations.models import CareerRecommendation
        from lib import feature2
        job='Required skills: Python, Django, PostgreSQL\nPreferred skills: Docker\nRequirements: Minimum 1 year professional experience. Bachelor in Computer Science required.'
        for name,data,gold in self.documents:
            with self.subTest(format=name):
                self.api.force_authenticate(self.owner)
                uploaded=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile(name,data)},format='multipart')
                self.assertEqual(uploaded.status_code,201,response_body(uploaded))
                resume=Resume.objects.get(pk=uploaded.data['data']['id'])
                self.assertTrue(resume.extracted_text)
                self.assertEqual(resume.user_id,self.owner.pk)
                self.assertEqual(resume.extraction_quality,uploaded.data['data']['extraction_quality'])
                match=self.api.post('/api/analysis/match/',{'resume_id':str(resume.pk),'job_text':job},format='json')
                self.assertEqual(match.status_code,201,response_body(match))
                saved=JobMatch.objects.get(pk=match.data['data']['id'])
                self.assertEqual(saved.analysis_metadata,match.data['data']['analysis_metadata'])
                self.assertEqual(saved.analysis_metadata['semantic_model'],'all-MiniLM-L6-v2')
                self.assertEqual(saved.analysis_metadata['extraction_quality'],resume.extraction_quality)
                self.assertEqual(match.data['data']['extraction_quality'],resume.extraction_quality)
                self.assertIsNone(saved.experience_score)
                self.assertIsNone(saved.analysis_metadata['experience']['estimated_cv_years'])
                detail=self.api.get(f'/api/analysis/match/{saved.pk}/')
                history=self.api.get('/api/analysis/matches/')
                self.assertEqual(detail.data['data']['analysis_metadata'],saved.analysis_metadata)
                found=next(item for item in history.data['data']['results'] if item['id']==str(saved.pk))
                self.assertEqual(found['analysis_metadata'],saved.analysis_metadata)
                prediction=feature2.predict_career_categories(resume.extracted_text)
                career=self.api.post(reverse('recommendation-generate'),{'resume_id':str(resume.pk)},format='json')
                self.assertEqual(career.status_code,201,response_body(career))
                stored=CareerRecommendation.objects.get(pk=career.data['id'])
                self.assertEqual(stored.profile_summary,career.data['profile_summary'])
                self.assertEqual(stored.profile_summary['extraction_quality'],resume.extraction_quality)
                self.assertEqual(career.data['extraction_quality'],resume.extraction_quality)
                self.assertEqual(stored.profile_summary['category_probabilities'],prediction['probabilities'])
                classifier,vectorizer=feature2._load_model()
                self.assertEqual(type(classifier).__name__,'LogisticRegression')
                self.assertEqual(type(vectorizer).__name__,'TfidfVectorizer')
                rec_detail=self.api.get(reverse('recommendation-detail',kwargs={'pk':stored.pk}))
                rec_history=self.api.get(reverse('recommendation-list'))
                rows=rec_history.data if isinstance(rec_history.data,list) else rec_history.data['results']
                found=next(item for item in rows if item['id']==str(stored.pk))
                self.assertEqual(found['top_roles'],rec_detail.data['top_roles'])
                self.assertEqual(found['profile_summary'],stored.profile_summary)
                for role in career.data['top_roles']:
                    self.assertEqual(role['salary_range'],'')
                    self.assertEqual(role['salary_metadata']['status'],'unknown')
                    if role['requirements_status']=='unknown':self.assertIsNone(role['match_percentage'])
                self.api.force_authenticate(self.other)
                self.assertIn(self.api.get(f'/api/analysis/match/{saved.pk}/').status_code,[403,404])
                self.assertIn(self.api.get(reverse('recommendation-detail',kwargs={'pk':stored.pk})).status_code,[403,404])
                self.api.force_authenticate(user=None)
                self.assertIn(self.api.get(f'/api/analysis/match/{saved.pk}/').status_code,[401,403])
                self.assertIn(self.api.get(reverse('recommendation-detail',kwargs={'pk':stored.pk})).status_code,[401,403])

    def test_failed_extraction_does_not_create_resume_or_invent_content(self):
        from unittest.mock import patch
        from resumes import extraction
        for name,data in [('empty.pdf',b''),('corrupt.pdf',b'%PDF-not-valid')]:
            response=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile(name,data)},format='multipart')
            self.assertEqual(response.status_code,400,response_body(response))
        with patch.object(extraction,'_ocr_pdf_page',side_effect=RuntimeError('Controlled OCR failure')):
            response=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile('failed-scan.pdf',self.documents[1][1])},format='multipart')
        self.assertEqual(response.status_code,400,response_body(response))
        self.assertEqual(response.data['error']['details']['extraction_quality']['status'],'failed')
        self.assertEqual(response.data['error']['details']['extraction_quality']['failed_pages'],[1])
        self.assertEqual(Resume.objects.filter(user=self.owner).count(),0)


    def test_partial_quality_is_preserved_in_both_histories_without_rescoring(self):
        import pymupdf as fitz
        from unittest.mock import patch
        from django.urls import reverse
        from resumes import extraction
        from recommendations.models import CareerRecommendation
        doc=fitz.open(stream=self.documents[0][1],filetype='pdf')
        scan=fitz.open(stream=self.documents[1][1],filetype='pdf');doc.insert_pdf(scan)
        data=doc.tobytes();doc.close();scan.close()
        with patch.object(extraction,'_ocr_pdf_page',side_effect=RuntimeError('PRIVATE_STORAGE_PATH_NOT_FOR_RESPONSE')):
            uploaded=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile('mixed.pdf',data)},format='multipart')
        self.assertEqual(uploaded.status_code,201,response_body(uploaded))
        quality=uploaded.data['data']['extraction_quality']
        self.assertEqual(quality['status'],'partial')
        self.assertEqual(quality['failed_pages'],[2])
        self.assertNotIn('PRIVATE_STORAGE_PATH',str(uploaded.data))
        resume=Resume.objects.get(pk=uploaded.data['data']['id'])
        self.assertEqual(resume.extraction_quality,quality)
        match=self.api.post('/api/analysis/match/',{'resume_id':str(resume.pk),'job_text':'Required skills: Python, Django, PostgreSQL.'},format='json')
        self.assertEqual(match.status_code,201,response_body(match))
        metadata=match.data['data']['analysis_metadata']
        self.assertEqual(metadata['extraction_quality'],quality)
        self.assertEqual(metadata['input_assessment_status'],'limited_by_extraction')
        career=self.api.post(reverse('recommendation-generate'),{'resume_id':str(resume.pk)},format='json')
        self.assertEqual(career.status_code,201,response_body(career))
        saved=CareerRecommendation.objects.get(pk=career.data['id'])
        self.assertEqual(saved.profile_summary['extraction_quality'],quality)
        self.assertEqual(saved.profile_summary['input_assessment_status'],'limited_by_extraction')
        # Later input metadata changes must not rewrite the saved explanation.
        resume.parsed_sections={'other_metadata':'preserved'};resume.save(update_fields=['parsed_sections'])
        self.assertEqual(resume.extraction_quality['status'],'unknown')
        detail=self.api.get(f"/api/analysis/match/{match.data['data']['id']}/")
        history=self.api.get('/api/analysis/matches/')
        self.assertEqual(detail.data['data']['extraction_quality'],quality)
        self.assertEqual(history.data['data']['results'][0]['analysis_metadata']['extraction_quality'],quality)
        detail=self.api.get(reverse('recommendation-detail',kwargs={'pk':saved.pk}))
        history=self.api.get(reverse('recommendation-list'))
        rows=history.data if isinstance(history.data,list) else history.data['results']
        self.assertEqual(detail.data['extraction_quality'],quality)
        self.assertEqual(rows[0]['extraction_quality'],quality)

    def test_legacy_resume_quality_unknown_without_modifying_data(self):
        from django.urls import reverse
        from recommendations.models import CareerRecommendation
        resume=Resume.objects.create(user=self.owner,original_filename='legacy.pdf',cv_file='legacy.pdf',extracted_text='Skills: Python, Django, SQL. Projects: Used Python in a student project.',parsed_sections={'existing_section':'keep'})
        self.assertEqual(resume.extraction_quality['status'],'unknown')
        rec=CareerRecommendation.objects.create(user=self.owner,resume=resume,dominant_category='Historical',profile_summary={})
        response=self.api.get(reverse('recommendation-detail',kwargs={'pk':rec.pk}))
        self.assertEqual(response.data['extraction_quality']['status'],'unknown')
        resume.refresh_from_db();rec.refresh_from_db()
        self.assertEqual(resume.parsed_sections,{'existing_section':'keep'})
        self.assertEqual(rec.profile_summary,{})


    def test_shared_education_upload_original_models_api_database_and_history(self):
        from docx import Document
        from django.urls import reverse
        from recommendations.models import CareerRecommendation
        from lib import feature2
        cases=[
            ('completed',"Education: Completed Bachelor's degree in Computer Science",'bachelor','completed'),
            ('progress',"Education: Currently pursuing Bachelor's degree in Computer Science",None,'in_progress'),
            ('course','Certifications: Bachelor-level Python course',None,'unknown'),
            ('certification','Certifications: Certified in Data Engineering',None,'unknown'),
            ('field_only','Summary: Fresh graduate in Data Science',None,'unknown'),
            ('bilingual','Pendidikan: Sedang menempuh S1 Teknik Informatika',None,'in_progress'),
            ('ambiguous','Education and Certifications\nBachelor-level Python course',None,'unknown'),
            ('mixed',"Education: Completed Bachelor's degree in Computer Science; Python training course.",'bachelor','completed'),
            ('aspiration',"Objective: I want to pursue Bachelor's degree in Computer Science",None,'unknown'),
        ]
        for name,education_text,level,completion in cases:
            with self.subTest(case=name):
                text=education_text+'\nSkills: Python, Django, SQL.\nProjects: Used Python in a student project.'
                doc=Document()
                for line in text.splitlines():doc.add_paragraph(line)
                buffer=io.BytesIO();doc.save(buffer)
                uploaded=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile(name+'.docx',buffer.getvalue())},format='multipart')
                self.assertEqual(uploaded.status_code,201,response_body(uploaded))
                resume=Resume.objects.get(pk=uploaded.data['data']['id'])
                direct=feature2.predict_career_categories(resume.extracted_text)
                first=self.api.post('/api/analysis/match/',{'resume_id':str(resume.pk),'job_text':'Required skills: Python, Django. Bachelor in Computer Science required.'},format='json')
                second=self.api.post(reverse('recommendation-generate'),{'resume_id':str(resume.pk)},format='json')
                self.assertEqual(first.status_code,201,response_body(first))
                self.assertEqual(second.status_code,201,response_body(second))
                first_profile=first.data['data']['analysis_metadata']['cv_understanding']['education']
                second_profile=second.data['profile_summary']['cv_understanding']['education']
                self.assertEqual(first_profile,second_profile)
                self.assertEqual(first_profile['level'],level)
                self.assertEqual(first_profile['completion_status'],completion)
                if level is None:self.assertIsNone(first.data['data']['scores']['education'])
                if name=='field_only':self.assertEqual(first_profile['field'],'data science')
                self.assertEqual(second.data['profile_summary']['category_probabilities'],direct['probabilities'])
                saved_first=JobMatch.objects.get(pk=first.data['data']['id'])
                saved_second=CareerRecommendation.objects.get(pk=second.data['id'])
                self.assertEqual(saved_first.analysis_metadata['cv_understanding']['education'],first_profile)
                self.assertEqual(saved_second.profile_summary['cv_understanding']['education'],first_profile)
                # History must retain the original snapshot, even if input changes.
                resume.extracted_text='Certifications: Bachelor-level Docker course.'
                resume.save(update_fields=['extracted_text'])
                detail=self.api.get(f'/api/analysis/match/{saved_first.pk}/')
                self.assertEqual(detail.data['data']['analysis_metadata']['cv_understanding']['education'],first_profile)
                history=self.api.get('/api/analysis/matches/')
                found=next(x for x in history.data['data']['results'] if x['id']==str(saved_first.pk))
                self.assertEqual(found['analysis_metadata']['cv_understanding']['education'],first_profile)
                detail=self.api.get(reverse('recommendation-detail',kwargs={'pk':saved_second.pk}))
                self.assertEqual(detail.data['profile_summary']['cv_understanding']['education'],first_profile)
                history=self.api.get(reverse('recommendation-list'))
                rows=history.data if isinstance(history.data,list) else history.data['results']
                found=next(x for x in rows if x['id']==str(saved_second.pk))
                self.assertEqual(found['profile_summary']['cv_understanding']['education'],first_profile)

    def test_final_headingless_evidence_and_semantic_policy_snapshot_original_models(self):
        from docx import Document
        from django.urls import reverse
        from lib import feature2
        text='Used Python and Django in an academic project. I have no experience with Kubernetes.\nEducation: Bachelor-level Python course.'
        doc=Document();doc.add_paragraph(text);buffer=io.BytesIO();doc.save(buffer)
        upload=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile('synthetic-evidence.docx',buffer.getvalue())},format='multipart')
        self.assertEqual(upload.status_code,201,response_body(upload))
        resume=Resume.objects.get(pk=upload.data['data']['id'])
        direct=feature2.predict_career_categories(resume.extracted_text)
        first=self.api.post('/api/analysis/match/',{'resume_id':str(resume.pk),'job_text':'Required: Python, Django. Bachelor in Computer Science required.'},format='json')
        second=self.api.post(reverse('recommendation-generate'),{'resume_id':str(resume.pk)},format='json')
        self.assertEqual(first.status_code,201,response_body(first));self.assertEqual(second.status_code,201,response_body(second))
        saved=first.data['data']['analysis_metadata']
        policy=saved['semantic_input']
        self.assertTrue(policy['filter_applied'])
        self.assertEqual(policy['policy_version'],'asserted_text_v1')
        self.assertNotIn('text',policy)
        self.assertEqual(second.data['profile_summary']['category_probabilities'],direct['probabilities'])
        for profile in [saved['cv_understanding'],second.data['profile_summary']['cv_understanding']]:
            python=next(s for s in profile['skills'] if s['name']=='python')
            self.assertEqual(python['evidence_items'][0]['source'],'projects')
            self.assertIsNone(profile['education']['level'])
            self.assertNotIn('kubernetes',{s['name'] for s in profile['skills']})
        resume.extracted_text='Skills: Kubernetes';resume.save(update_fields=['extracted_text'])
        history=self.api.get('/api/analysis/matches/')
        found=next(x for x in history.data['data']['results'] if x['id']==first.data['data']['id'])
        self.assertEqual(found['analysis_metadata']['semantic_input'],policy)
        self.assertEqual(found['extraction_quality'],upload.data['data']['extraction_quality'])

    def test_requirement_recognition_education_and_freelance_snapshots_original_models(self):
        from docx import Document
        from django.urls import reverse
        from lib import feature2
        cases=[
            ('Education: Completed Bachelor in Computer Science\nSkills: Python', '**Required Skills:**\n- Python\n- ZorgDB\n**Education Requirements:**\nCompleted Bachelor in Computer Science required.',1,'completed'),
            ('Selected Freelance Work\nFrontend Contractor May 2025 - September 2026\nSkills: HTML5, CSS3, JavaScript\nEducation: Completed Bachelor in Computer Science', 'Required skills: HTML, CSS\nExperience requirements: Minimum 1 year relevant experience; freelance accepted.\nEducation requirements: Completed Bachelor in Computer Science required.',0,'completed'),
            ('Education: Currently pursuing Bachelor in Computer Science\nSkills: Python\nInternship\nDeveloper Intern Jan 2025 - Apr 2025','Required skills: Python\nExperience requirements: Full-time experience is not required; internships accepted.\nEducation requirements: Currently pursuing or completed Bachelor in Computer Science. Final-year students are welcome.',0,'in_progress')]
        for text,job,unresolved,completion in cases:
            with self.subTest(completion=completion,unresolved=unresolved):
                document=Document();document.add_paragraph(text);buffer=io.BytesIO();document.save(buffer)
                upload=self.api.post('/api/resume/upload/',{'cv_file':SimpleUploadedFile('synthetic-policy.docx',buffer.getvalue())},format='multipart')
                self.assertEqual(upload.status_code,201,response_body(upload))
                resume=Resume.objects.get(pk=upload.data['data']['id'])
                direct=feature2.predict_career_categories(resume.extracted_text)
                first=self.api.post('/api/analysis/match/',{'resume_id':str(resume.pk),'job_text':job},format='json')
                second=self.api.post(reverse('recommendation-generate'),{'resume_id':str(resume.pk)},format='json')
                self.assertEqual(first.status_code,201,response_body(first));self.assertEqual(second.status_code,201,response_body(second))
                metadata=first.data['data']['analysis_metadata']
                coverage=metadata['job_understanding']['requirement_coverage']
                self.assertEqual(coverage['unresolved'],unresolved)
                self.assertEqual(coverage['matched']+coverage['unmatched']+coverage['unresolved'],coverage['total'])
                self.assertEqual(metadata['cv_understanding']['education'],second.data['profile_summary']['cv_understanding']['education'])
                self.assertEqual(metadata['cv_understanding']['education']['completion_status'],completion)
                self.assertEqual(second.data['profile_summary']['category_probabilities'],direct['probabilities'])
                resume.extracted_text='Skills: Docker';resume.parsed_sections={};resume.save(update_fields=['extracted_text','parsed_sections'])
                history=self.api.get('/api/analysis/matches/')
                row=next(x for x in history.data['data']['results'] if x['id']==first.data['data']['id'])
                self.assertEqual(row['analysis_metadata']['job_understanding'],metadata['job_understanding'])
                self.assertEqual(row['extraction_quality'],upload.data['data']['extraction_quality'])
