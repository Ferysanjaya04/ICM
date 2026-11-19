"""Regression checks for improved Feature 1. No DB and no network required.

Run from backend/: python manage.py test analysis.tests_feature1_v2 -v 2
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib import feature1 as f


class Feature1V2Tests(unittest.TestCase):
    def setUp(self):
        self.skills = {
            "languages": ["Python", "JavaScript", "TypeScript", "Go"],
            "frameworks": ["Django", "React", "Node.js"],
            "databases": ["PostgreSQL"],
            "other": ["Docker", "AWS"],
        }

    def test_skill_alias_and_word_boundary(self):
        skills = f.extract_skills("Menguasai reactjs, postgres, node js dan JS.", self.skills)
        self.assertEqual(skills, ["javascript", "node.js", "postgresql", "react"])
        self.assertNotIn("go", f.extract_skills("Google cloud tutorials", self.skills))

    def test_skill_database_uses_explicit_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skills_database.json"
            path.write_text(json.dumps(self.skills), encoding="utf-8")
            self.assertEqual(f.load_skills_database(str(path))["languages"][0], "Python")

    def test_missing_job_skills_is_unknown_not_100(self):
        self.assertIsNone(f.calculate_skill_score(["python"], []))

    def test_skill_score_set_based(self):
        self.assertEqual(f.calculate_skill_score(["python", "python"], ["python", "django"]), 50.0)

    def test_weighting_unchanged_from_proposal(self):
        self.assertEqual(f.calculate_compatibility_score(80, 90, 70, 60), (79.0, "MEDIUM"))
        self.assertEqual(f.calculate_compatibility_score(80, 90, None, 70), (83.13, "HIGH"))

    def test_all_none_is_undetermined(self):
        self.assertEqual(f.calculate_compatibility_score(None, None, None, None), (None, "UNDETERMINED"))

    def test_unknown_components_do_not_get_perfect_scores(self):
        self.assertEqual(f.calculate_education_score(2, 0, "computer science", None)[0], None)
        self.assertEqual(f.calculate_experience_score(None, None, {}, False, False)[0], None)

    def test_year_range_parsing(self):
        parsed = f.parse_period("2020 - 2023")
        self.assertEqual(parsed["duration_months"], 36)
        self.assertIsNone(parsed["start_month"])

    def test_month_range_parsing(self):
        parsed = f.parse_period("Jan 2022 - Desember 2023")
        self.assertEqual(parsed["duration_months"], 24)

    def test_invalid_periods_ignored(self):
        self.assertIsNone(f.parse_period("Des 2024 - Jan 2021")["duration_months"])

    def test_generic_period_extraction_with_sections(self):
        cv = ("PENGALAMAN KERJA\nBackend Developer di Perusahaan XYZ\nJan 2022 - Des 2023\n"
              "PENDIDIKAN\nPoliteknik A\n2020 - 2024\n"
              "PROYEK\nAplikasi kasir\nJan 2024 - Mar 2024")
        result = f.extract_entry_periods(cv)
        self.assertEqual([x["category"] for x in result], ["work", "education", "project"])
        self.assertEqual(result[0]["duration_months"], 24)
        self.assertEqual(f._unique_work_months(result), 24)

    def test_overlapping_experiences_not_double_counted(self):
        cv = ("WORK EXPERIENCE\nBackend Developer\nJan 2022 - Dec 2023\n"
              "Cloud Engineer\nJan 2023 - Dec 2024")
        self.assertEqual(f._unique_work_months(f.extract_entry_periods(cv)), 36)

    def test_internship_duration_is_separate_from_professional_estimation(self):
        cv = "MAGANG\nIT Support Intern\nJan 2024 - Jun 2024"
        result = f.extract_entry_periods(cv)
        self.assertEqual(result[0]["category"], "internship")
        # The old assertion conflated internship and professional duration.
        self.assertEqual(f._unique_work_months(result), 0)
        self.assertEqual(f._unique_work_months(result, ("internship",)), 6)

    def test_job_experience_range_uses_lower_bound(self):
        self.assertEqual(f.extract_explicit_experience_years("2-5 years experience", prefer_min=True), 2)

    def test_education_with_context(self):
        cv = "EDUCATION\nS1 Teknik Informatika, Universitas ABC\nSKILLS\nPython, React"
        self.assertEqual(f.get_education_level(cv), 2)
        self.assertEqual(f.get_education_field(cv), "teknik informatika")
        self.assertEqual(f.get_education_level("Bachelor in Computer Science"), 2)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            f.analyze_cv_job("", "Backend Developer")
        with self.assertRaises(ValueError):
            f.analyze_cv_job("Python developer", "")

    def test_complete_pipeline_preserves_service_contract(self):
        cv = ("PENGALAMAN KERJA\nBackend Developer\nJan 2022 - Des 2023\n"
              "PENDIDIKAN\nS1 Teknik Informatika\nSKILLS\nPython, Django, PostgreSQL")
        job = "Backend Developer with Python, Django, PostgreSQL and Docker. S1 Teknik Informatika. 2 years experience."
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skills_database.json"
            path.write_text(json.dumps(self.skills), encoding="utf-8")
            with patch.object(f, "calculate_semantic_score", return_value=80.0):
                result = f.analyze_cv_job(cv, job, "cv.pdf", str(path))
        self.assertEqual(result["feature"], "cv_vs_job_requirement")
        self.assertEqual(result["skills"]["missing_or_not_detected"], ["docker"])
        self.assertEqual(result["scores"]["experience"], 100.0)
        self.assertEqual(result["scores"]["skill"], 75.0)
        self.assertIn(result["compatibility"]["level"], ("LOW", "MEDIUM", "HIGH"))
        self.assertIsInstance(result["recommendations"], list)
        self.assertEqual(result["scoring_info"]["observed_weight"], 1.0)

    def test_unknown_skill_dimension_documented_in_output(self):
        cv = "Data enthusiast interested in career opportunities in technology."
        job = "Build reliable solutions for users and collaborate across teams."
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skills_database.json"
            path.write_text(json.dumps(self.skills), encoding="utf-8")
            with patch.object(f, "calculate_semantic_score", return_value=64.0):
                result = f.analyze_cv_job(cv, job, skills_db_path=str(path))
        self.assertIsNone(result["scores"]["skill"])
        self.assertTrue(any("tidak terdeteksi" in r for r in result["recommendations"]))
        self.assertLess(result["scoring_info"]["observed_weight"], 1.0)


    def analyze_evidence(self, cv, job="Python Django Docker Kubernetes. Minimum 2 years experience. Bachelor in Computer Science."):
        with patch.object(f, "calculate_semantic_score", return_value=80.0):
            return f.analyze_cv_job(cv, job)

    def test_cv_evidence_replaces_legacy_keyword_detection_and_job_detector_stays_separate(self):
        cv = "Skills: Python\nProjects: Built services using Django.\nSummary: No Docker experience. Interested in Kubernetes."
        legacy = f.extract_skills(cv, f.load_skills_database())
        self.assertTrue({"python", "django", "docker", "kubernetes"}.issubset(legacy))
        result = self.analyze_evidence(cv)
        self.assertEqual(result["skills"]["cv"], ["django", "python"])
        self.assertEqual(result["skills"]["matched"], ["django", "python"])
        self.assertEqual(result["skills"]["missing_or_not_detected"], ["docker", "kubernetes"])
        self.assertEqual(result["scores"]["skill"], 50.0)
        self.assertEqual({s["name"] for s in result["skills"]["excluded_mentions"]}, {"docker", "kubernetes"})
        self.assertEqual(set(result["skills"]["job_requirement"]), {"python", "django", "docker", "kubernetes"})

    def test_professional_duration_excludes_projects_and_internships(self):
        cv = ("Experience\nPersonal Project Jan 2022 - Dec 2023\nUsed Django.\n"
              "Backend Developer Intern Jan 2024 - Jun 2024\nUsed Python.")
        result = self.analyze_evidence(cv)
        self.assertIsNone(result["scores"]["experience"])
        self.assertIsNone(result["experience"]["estimated_cv_years"])
        self.assertEqual(result["cv_understanding"]["experience"]["internship_months"], 6)
        self.assertEqual([e["category"] for e in result["experience"]["period_details"]], ["project", "internship"])

    def test_duration_requires_positive_professional_time_evidence(self):
        for cv in (
            "Projects: 4 years experience using Python and Django",
            "Summary: Backend Developer with no 4 years experience using Python",
            "Objective: Seeking Backend Developer role requiring 4 years experience with Python",
            "Work Experience: Backend Developer with 2-5 years experience using Python",
            "Work Experience: Backend Developer using Python and Django",
        ):
            with self.subTest(cv=cv):
                result = self.analyze_evidence(cv)
                self.assertIsNone(result["scores"]["experience"])
        result = self.analyze_evidence("Work Experience: Backend Developer with 3 years experience using Python")
        self.assertEqual(result["experience"]["explicit_cv_years"], 3.0)
        self.assertEqual(result["scores"]["experience"], 100.0)
        self.assertIsNone(f.extract_explicit_experience_years("2-5 years experience"))
        self.assertEqual(f.extract_explicit_experience_years("2-5 years experience", prefer_min=True), 2)

    def test_unheaded_professional_timeline_is_supported(self):
        result = self.analyze_evidence("Backend Developer\nJan 2022 - Dec 2023\nUsed Python and Django.")
        self.assertEqual(result["experience"]["estimated_cv_years"], 2.0)
        self.assertEqual(result["scores"]["experience"], 100.0)

    def test_coverage_discloses_unknowns_without_changing_weights_or_formula(self):
        result = self.analyze_evidence("Skills: Python, Django")
        self.assertIsNone(result["scores"]["education"])
        self.assertIsNone(result["scores"]["experience"])
        info = result["scoring_info"]
        self.assertEqual(info["base_weights"], {"semantic": .25, "skill": .40, "experience": .20, "education": .15})
        self.assertEqual(info["assessment_status"], "partial")
        self.assertEqual(info["observed_weight"], .65)
        self.assertEqual(info["unknown_components"], ["experience", "education"])
        self.assertAlmostEqual(info["effective_weights"]["semantic"], .25/.65, places=5)
        self.assertEqual(result["compatibility"]["score"], 61.54)
        self.assertEqual(f.calculate_compatibility_score(80, 90, 70, 60), (79.0, "MEDIUM"))

    def test_no_measurable_components_stays_undetermined(self):
        with patch.object(f, "calculate_semantic_score", return_value=None):
            result = f.analyze_cv_job("A candidate profile without declared details", "A role without technical or duration requirements")
        self.assertEqual(result["compatibility"], {"score": None, "level": "UNDETERMINED"})
        self.assertTrue(all(s is None for s in result["scores"].values()))
        self.assertEqual(result["scoring_info"]["observed_weight"], 0)
        self.assertEqual(result["scoring_info"]["assessment_status"], "undetermined")

    def test_unrelated_negative_skill_sentence_does_not_erase_valid_work_dates(self):
        result = self.analyze_evidence("Work Experience: Backend Developer Jan 2022 - Dec 2023. No Docker experience. Used Python.")
        self.assertEqual(result["experience"]["estimated_cv_years"], 2.0)
        self.assertEqual(result["scores"]["experience"], 100.0)
        self.assertNotIn("docker", result["skills"]["cv"])

    def test_future_month_period_is_not_treated_as_completed_work(self):
        from datetime import date
        with patch.object(f, "date") as clock:
            clock.today.return_value = date(2026, 5, 20)
            self.assertIsNone(f.parse_period("Jan 2026 - Nov 2026")["duration_months"])

    def test_unicode_date_separators_keep_valid_duration(self):
        for separator in ("–", "—"):
            with self.subTest(separator=separator):
                result = self.analyze_evidence(f"Work Experience: Backend Developer Jan 2022 {separator} Dec 2023 using Python")
                self.assertEqual(result["experience"]["estimated_cv_years"], 2.0)

    def test_degree_dates_under_generic_experience_are_not_professional_work(self):
        result = self.analyze_evidence("Experience\nBachelor in Computer Science Jan 2020 - Dec 2023\nSkills: Python")
        self.assertIsNone(result["scores"]["experience"])
        self.assertEqual(result["experience"]["period_details"][0]["category"], "education")

    def test_explicit_professional_years_are_supported(self):
        result = self.analyze_evidence("Backend Developer with 3 years of professional experience using Python")
        self.assertEqual(result["experience"]["explicit_cv_years"], 3.0)
        self.assertEqual(result["scores"]["experience"], 100.0)

if __name__ == "__main__":
    unittest.main()


class Feature1IntelligenceTests(unittest.TestCase):
    def analyze(self, cv, job='Required skills: Python. Minimum 1 year professional experience. Bachelor in Computer Science required.'):
        with patch.object(f, 'calculate_semantic_score', return_value=80):
            return f.analyze_cv_job(cv, job)

    def test_training_is_not_professional_employment(self):
        cv='Work Experience\nBackend Developer\nJan 2022 - Dec 2022\nTraining\nData Engineering Course Jan 2023 - Dec 2025\nUsed Python.'
        result=self.analyze(cv)
        self.assertEqual(result['experience']['estimated_cv_years'],1)
        self.assertEqual(len(result['experience']['period_details']),1)
        self.assertTrue(result['cv_understanding']['certifications'])

    def test_course_and_target_degree_are_not_candidate_degrees(self):
        for cv in ['Certifications\nBachelor level Python course.', 'Training: Master in Computer Science course.', 'Job Requirements: Bachelor in Computer Science\nSkills: Python', 'Summary: Lulusan baru Sains Data dan Informatika.']:
            with self.subTest(cv=cv):
                result=self.analyze(cv)
                self.assertIsNone(result['scores']['education'])
                self.assertIsNone(result['cv_understanding']['education']['level'])

    def test_in_progress_and_completed_degrees(self):
        ongoing=self.analyze('Education\nPursuing Bachelor in Computer Science\nSkills: Python')
        self.assertIsNone(ongoing['scores']['education'])
        self.assertEqual(ongoing['cv_understanding']['education']['entries'][0]['status'],'in_progress')
        completed=self.analyze('Education\nGraduated Bachelor in Computer Science\nSkills: Python')
        self.assertEqual(completed['scores']['education'],100)

    def test_required_preferred_and_responsibilities(self):
        result=self.analyze('Skills: Python','Required skills: Python\nPreferred skills: Docker\nResponsibilities: Maintain Kubernetes services.')
        self.assertEqual(result['skills']['job_requirement'],['python'])
        self.assertEqual(result['scores']['skill'],100)
        self.assertEqual(result['job_understanding']['preferred_skills'],['docker'])
        self.assertEqual(result['job_understanding']['responsibility_skills'],['kubernetes'])

    def test_optional_experience_and_degree_not_hard_requirements(self):
        result=self.analyze('Education: Bachelor in Computer Science\nSkills: Python', 'Required skills: Python\nPreferred: Master in Computer Science. 3 years experience preferred.')
        self.assertIsNone(result['scores']['education'])
        self.assertIsNone(result['experience']['required_years'])
        self.assertEqual(result['scoring_info']['observed_weight'],.65)

    def test_responsibility_only_and_ambiguous_ads(self):
        result=self.analyze('Skills: Python', 'Responsibilities: Build Python services using Docker.')
        self.assertIsNone(result['scores']['skill'])
        self.assertEqual(result['job_understanding']['responsibility_skills'],['docker','python'])
        ambiguous=self.analyze('Skills: Python','Python Docker')
        self.assertEqual(ambiguous['scores']['skill'],50)
        self.assertEqual(ambiguous['job_understanding']['classification_status'],'ambiguous')
        self.assertTrue(ambiguous['job_understanding']['warnings'])

    def test_bilingual_free_requirements_and_negative_requirements(self):
        result=self.analyze('Skills: Python','Harus menguasai Python. Docker diutamakan.\nTanggung jawab: Mengembangkan Kubernetes services.')
        self.assertEqual(result['skills']['job_requirement'],['python'])
        negative=self.analyze('Skills: Python','Required: Python. No Docker required. No Bachelor degree required.')
        self.assertEqual(negative['skills']['job_requirement'],['python'])
        self.assertIsNone(negative['scores']['education'])

    def test_overlap_union_cross_year_and_separate_internship(self):
        result=self.analyze('Work Experience\nBackend Developer Jan 2022 - Dec 2023\nBackend Engineer Jan 2023 - Dec 2024\nMagang\nData Engineer Intern September 2025 - Desember 2025\nProjects\nUsed Python Juni–Agustus 2025')
        self.assertEqual(result['experience']['estimated_cv_years'],3)
        self.assertEqual(result['cv_understanding']['experience']['internship_months'],4)
        self.assertEqual([x['duration_months'] for x in result['experience']['period_details']],[24,24,4,3])

    def test_incomplete_and_missing_dates_are_unknown(self):
        for period in ['Jan 2022 - 2024','Jan 2022 -','Jan 2024 - Feb 2023','']:
            with self.subTest(period=period):
                result=self.analyze('Work Experience\nBackend Developer\n'+period+'\nSkills: Python')
                self.assertIsNone(result['experience']['estimated_cv_years'])
                self.assertIsNone(result['scores']['experience'])

    def test_active_and_short_indonesian_periods(self):
        from datetime import date
        today=date.today()
        active=f.parse_period(f'Jan {today.year} - Present')
        self.assertEqual(active['duration_months'],today.month)
        self.assertEqual(f.parse_period('Juni–Agustus 2025')['duration_months'],3)
        self.assertIsNone(f.parse_period('Desember–Januari 2025')['duration_months'])

    def test_project_intern_and_fresh_grad_not_one_year_professional(self):
        result=self.analyze('Summary: Fresh graduate\nProjects\nUsed Python Jan 2025 - Dec 2025\nInternship\nJunior Data Engineer September 2025 - Desember 2025')
        self.assertIsNone(result['scores']['experience'])
        self.assertEqual(result['experience']['assessment_status'],'unknown')
        self.assertTrue(result['experience']['internship'])
        self.assertTrue(result['experience']['project_experience'])
        self.assertEqual(result['scoring_info']['observed_weight'],.65)


    def test_year_only_work_estimates_do_not_meet_professional_duration(self):
        result=self.analyze('Work Experience\nBackend Developer 2022 - 2024\nSkills: Python')
        self.assertIsNone(result['scores']['experience'])
        self.assertEqual(result['experience']['period_details'][0]['precision'],'year_estimate')

    def test_negative_requirement_does_not_erase_other_requirement_lines(self):
        result=self.analyze('Skills: Python','Required skills:\nPython\nNo Docker required')
        self.assertEqual(result['skills']['job_requirement'],['python'])


    def test_job_certificate_and_master_verb_are_not_academic_requirements(self):
        for job in ['Required: Scrum Master certification', 'Required: Master Python', 'Required: Bachelor level Python course']:
            with self.subTest(job=job):
                profile=f.understand_job_requirements(job,f.load_skills_database())
                self.assertEqual(profile['education_level'],0)
