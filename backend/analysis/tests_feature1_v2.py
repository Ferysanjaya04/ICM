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

    def test_internship_is_included_in_estimation(self):
        cv = "MAGANG\nIT Support Intern\nJan 2024 - Jun 2024"
        result = f.extract_entry_periods(cv)
        self.assertEqual(result[0]["category"], "internship")
        self.assertEqual(f._unique_work_months(result), 6)

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


if __name__ == "__main__":
    unittest.main()
