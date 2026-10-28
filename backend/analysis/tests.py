"""
Tests untuk Analysis Feature - CV vs Job Requirement Matching
"""

from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from unittest import mock

from resumes.models import Resume
from recommendations.models import JobRole
from analysis.models import JobMatch
from analysis.services import AnalysisService

# Import fungsi scoring untuk unit testing
from lib.feature1 import calculate_compatibility_score


class AnalysisServiceTestCase(TestCase):
    """Test suite untuk AnalysisService"""
    
    def setUp(self):
        """Setup test data"""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.cv_text = """
        JOHANNES HUTAPEA
        SOFTWARE ENGINEER
        
        KEAHLIAN: Python, JavaScript, React, Node.js, PostgreSQL, Docker
        
        PENGALAMAN: 1 tahun pengalaman sebagai Junior Web Developer
        
        PENDIDIKAN: S1 Teknik Informatika dari Universitas Dian Nusantara
        """
        
        self.job_text = """
        JOB: Mid-Level Software Engineer
        
        REQUIREMENT: 1 tahun pengalaman
        SKILLS: Python, JavaScript, React, Node.js, PostgreSQL
        EDUCATION: Bachelor in Computer Science
        """
        
        # Create Resume
        self.resume = Resume.objects.create(
            user=self.user,
            original_filename="test_cv.pdf",
            cv_file="dummy.pdf",
            extracted_text=self.cv_text
        )
    
    def test_analyze_cv_and_job_success(self):
        """Test successful CV-Job analysis"""
        result = AnalysisService.analyze_cv_vs_job(
            cv_text=self.cv_text,
            job_text=self.job_text
        )
        
        # Check result structure
        self.assertIn("compatibility_score", result)
        self.assertIn("compatibility_level", result)
        self.assertIn("semantic_score", result)
        self.assertIn("skill_score", result)
        self.assertIn("experience_score", result)
        self.assertIn("education_score", result)
        self.assertIn("matched_skills", result)
        self.assertIn("missing_skills", result)
        self.assertIn("recommendations", result)
        
        # Check types
        self.assertIsInstance(result["compatibility_score"], Decimal)
        self.assertIsInstance(result["semantic_score"], Decimal)
        self.assertIsInstance(result["matched_skills"], list)
        self.assertIsInstance(result["recommendations"], list)
    
    def test_analyze_cv_and_job_invalid_cv_text(self):
        """Test dengan CV text kosong"""
        with self.assertRaises(ValueError):
            AnalysisService.analyze_cv_vs_job(
                cv_text="",
                job_text=self.job_text
            )
    
    def test_analyze_cv_and_job_invalid_job_text(self):
        """Test dengan Job text kosong"""
        with self.assertRaises(ValueError):
            AnalysisService.analyze_cv_vs_job(
                cv_text=self.cv_text,
                job_text=""
            )
    
    def test_analyze_cv_and_job_too_short_text(self):
        """Test dengan text yang terlalu pendek"""
        with self.assertRaises(ValueError):
            AnalysisService.analyze_cv_vs_job(
                cv_text="short",
                job_text=self.job_text
            )


class JobMatchModelTestCase(TestCase):
    """Test suite untuk JobMatch model"""
    
    def setUp(self):
        """Setup test data"""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            original_filename="test_cv.pdf",
            cv_file="dummy.pdf",
            extracted_text="Test CV"
        )
    
    def test_create_job_match(self):
        """Test membuat JobMatch record"""
        job_match = JobMatch.objects.create(
            user=self.user,
            resume=self.resume,
            job_title_target="Software Engineer",
            job_description_text="Job description",
            compatibility_score=Decimal("75.50"),
            semantic_score=Decimal("70.00"),
            skill_score=Decimal("80.00"),
            experience_score=Decimal("60.00"),
            education_score=Decimal("90.00"),
            compatibility_level="MEDIUM",
            matched_skills=["Python", "JavaScript"],
            missing_skills=["Docker"],
            recommendations=["Learn Docker"]
        )
        
        self.assertEqual(job_match.user, self.user)
        self.assertEqual(job_match.resume, self.resume)
        self.assertEqual(str(job_match.compatibility_score), "75.50")
        self.assertEqual(job_match.compatibility_level, "MEDIUM")
        self.assertIn("Python", job_match.matched_skills)
    
    def test_job_match_str(self):
        """Test string representation JobMatch"""
        job_match = JobMatch.objects.create(
            user=self.user,
            resume=self.resume,
            job_title_target="Engineer",
            job_description_text="Test",
            compatibility_score=Decimal("75.00"),
            semantic_score=Decimal("70.00"),
            skill_score=Decimal("80.00"),
            experience_score=Decimal("60.00"),
            education_score=Decimal("90.00"),
            compatibility_level="MEDIUM"
        )
        
        self.assertIn("75.00", str(job_match))
        self.assertIn("test_cv.pdf", str(job_match))


# ============================================================
# REGRESSION TESTS FOR COMPATIBILITY SCORE CALCULATION
# ============================================================

class CompatibilityScoringRegressionTestCase(TestCase):
    """
    Unit tests untuk calculate_compatibility_score() function.
    Memverifikasi weight normalization, None handling, dan boundary conditions.
    """
    
    # ============================================================
    # TEST A: All components available
    # ============================================================
    
    def test_calculate_compatibility_all_components(self):
        """
        Test Case A: Semua komponen tersedia
        Input: semantic=80, skill=90, experience=70, education=60
        Expected: 79.00 (MEDIUM)
        
        Formula: 80×0.25 + 90×0.40 + 70×0.20 + 60×0.15
               = 20 + 36 + 14 + 9
               = 79
        """
        score, level = calculate_compatibility_score(
            semantic_score=80.0,
            skill_score=90.0,
            experience_score=70.0,
            education_score=60.0
        )
        
        self.assertEqual(score, 79.0, 
                        f"Expected 79.0, got {score}")
        self.assertEqual(level, "MEDIUM",
                        f"Expected MEDIUM, got {level}")
    
    # ============================================================
    # TEST B: Experience = None (weight normalization)
    # ============================================================
    
    def test_calculate_compatibility_experience_none(self):
        """
        Test Case B: Experience = None (most common case)
        Input: semantic=80, skill=90, experience=None, education=70
        Expected: 83.13 (HIGH) dengan normalisasi bobot
        
        Available components: semantic, skill, education
        Total available weight: 0.25 + 0.40 + 0.15 = 0.80
        
        Formula: (80×0.25 + 90×0.40 + 70×0.15) / 0.80
               = (20 + 36 + 10.5) / 0.80
               = 66.5 / 0.80
               = 83.125 ≈ 83.13 (rounded to 2 decimals)
        """
        score, level = calculate_compatibility_score(
            semantic_score=80.0,
            skill_score=90.0,
            experience_score=None,  # None
            education_score=70.0
        )
        
        # Check score within acceptable range (±0.05 untuk rounding error)
        self.assertAlmostEqual(score, 83.13, delta=0.05,
                              msg=f"Expected ~83.13, got {score}")
        self.assertEqual(level, "HIGH",
                        f"Expected HIGH, got {level}")
    
    # ============================================================
    # TEST C: Semantic = None
    # ============================================================
    
    def test_calculate_compatibility_semantic_none(self):
        """
        Test Case C: Semantic = None
        Input: semantic=None, skill=80, experience=60, education=100
        Expected: 78.67 (MEDIUM) dengan normalisasi bobot
        
        Available components: skill, experience, education
        Total available weight: 0.40 + 0.20 + 0.15 = 0.75
        
        Formula: (80×0.40 + 60×0.20 + 100×0.15) / 0.75
               = (32 + 12 + 15) / 0.75
               = 59 / 0.75
               = 78.6667 ≈ 78.67
        """
        score, level = calculate_compatibility_score(
            semantic_score=None,  # None
            skill_score=80.0,
            experience_score=60.0,
            education_score=100.0
        )
        
        self.assertAlmostEqual(score, 78.67, delta=0.05,
                              msg=f"Expected ~78.67, got {score}")
        self.assertEqual(level, "MEDIUM",
                        f"Expected MEDIUM, got {level}")
    
    # ============================================================
    # TEST D: All components = None
    # ============================================================
    
    def test_calculate_compatibility_all_none(self):
        """
        Test Case D: Semua komponen = None
        Input: All None
        Expected: (None, "UNDETERMINED")
        
        Ketika tidak ada komponen yang tersedia, fungsi harus
        mengembalikan None dan level "UNDETERMINED".
        """
        score, level = calculate_compatibility_score(
            semantic_score=None,
            skill_score=None,
            experience_score=None,
            education_score=None
        )
        
        self.assertIsNone(score,
                         f"Expected None, got {score}")
        self.assertEqual(level, "UNDETERMINED",
                        f"Expected UNDETERMINED, got {level}")
    
    # ============================================================
    # TEST E: Invalid weight (zero or negative)
    # ============================================================
    
    def test_calculate_compatibility_invalid_weight(self):
        """
        Test Case E: Total bobot tidak valid
        
        Edge case: Jika semua komponen memiliki bobot nol
        (tidak mungkin dalam praktik, tapi guard harus ada)
        
        Expected: (None, "UNDETERMINED")
        """
        # Simulated edge case dengan mock
        with mock.patch('lib.feature1.WEIGHT_SEMANTIC', 0):
            with mock.patch('lib.feature1.WEIGHT_SKILL', 0):
                with mock.patch('lib.feature1.WEIGHT_EXPERIENCE', 0):
                    with mock.patch('lib.feature1.WEIGHT_EDUCATION', 0):
                        score, level = calculate_compatibility_score(
                            semantic_score=80.0,
                            skill_score=90.0,
                            experience_score=70.0,
                            education_score=60.0
                        )
                        
                        self.assertIsNone(score)
                        self.assertEqual(level, "UNDETERMINED")
    
    # ============================================================
    # TEST F: Boundary conditions (exactly 80, 60)
    # ============================================================
    
    def test_calculate_compatibility_boundary_high(self):
        """
        Boundary Test F1: Score exactly 80 → HIGH
        Input: All equal to 80
        Expected: 80.0 (HIGH)
        """
        score, level = calculate_compatibility_score(
            semantic_score=80.0,
            skill_score=80.0,
            experience_score=80.0,
            education_score=80.0
        )
        
        self.assertEqual(score, 80.0)
        self.assertEqual(level, "HIGH")
    
    def test_calculate_compatibility_boundary_medium_high(self):
        """
        Boundary Test F2: Score just below 80 → MEDIUM
        Input: Designed to produce 79.99
        Expected: 79.99 (MEDIUM, not HIGH)
        """
        # 79.99 is technically < 80
        score, level = calculate_compatibility_score(
            semantic_score=79.99,
            skill_score=79.99,
            experience_score=79.99,
            education_score=79.99
        )
        
        self.assertEqual(score, 79.99)
        self.assertEqual(level, "MEDIUM")
    
    def test_calculate_compatibility_boundary_medium(self):
        """
        Boundary Test F3: Score exactly 60 → MEDIUM
        Input: All equal to 60
        Expected: 60.0 (MEDIUM)
        """
        score, level = calculate_compatibility_score(
            semantic_score=60.0,
            skill_score=60.0,
            experience_score=60.0,
            education_score=60.0
        )
        
        self.assertEqual(score, 60.0)
        self.assertEqual(level, "MEDIUM")
    
    def test_calculate_compatibility_boundary_medium_low(self):
        """
        Boundary Test F4: Score just below 60 → LOW
        Input: Designed to produce 59.99
        Expected: 59.99 (LOW, not MEDIUM)
        """
        score, level = calculate_compatibility_score(
            semantic_score=59.99,
            skill_score=59.99,
            experience_score=59.99,
            education_score=59.99
        )
        
        self.assertEqual(score, 59.99)
        self.assertEqual(level, "LOW")
    
    def test_calculate_compatibility_boundary_low(self):
        """
        Boundary Test F5: Very low score → LOW
        Input: All equal to 30
        Expected: 30.0 (LOW)
        """
        score, level = calculate_compatibility_score(
            semantic_score=30.0,
            skill_score=30.0,
            experience_score=30.0,
            education_score=30.0
        )
        
        self.assertEqual(score, 30.0)
        self.assertEqual(level, "LOW")
    
    # ============================================================
    # TEST G: Multiple None components
    # ============================================================
    
    def test_calculate_compatibility_multiple_none(self):
        """
        Test Case H: Multiple komponen = None
        Input: semantic=80, skill=None, experience=None, education=90
        Expected: Correct renormalization dengan 2 komponen
        
        Available components: semantic, education
        Total available weight: 0.25 + 0.15 = 0.40
        
        Formula: (80×0.25 + 90×0.15) / 0.40
               = (20 + 13.5) / 0.40
               = 33.5 / 0.40
               = 83.75
        """
        score, level = calculate_compatibility_score(
            semantic_score=80.0,
            skill_score=None,
            experience_score=None,
            education_score=90.0
        )
        
        self.assertAlmostEqual(score, 83.75, delta=0.05)
        self.assertEqual(level, "HIGH")
    
    # ============================================================
    # TEST G: Service layer - None handling in _process_feature1_result()
    # ============================================================
    
    def test_process_feature1_result_with_none_experience(self):
        """
        Test Case G: Service layer None preservation
        
        Memverifikasi bahwa _process_feature1_result() 
        correctly mempertahankan None values saat konversi ke Decimal.
        """
        # Mock Feature 1 result dengan None experience_score
        feature1_result = {
            "compatibility": {
                "score": 85.5,
                "level": "HIGH"
            },
            "scores": {
                "semantic": 85.0,
                "skill": 90.0,
                "experience": None,  # None
                "education": 80.0
            },
            "skills": {
                "matched": ["Python", "Django"],
                "missing_or_not_detected": ["Docker"]
            },
            "recommendations": ["Learn Docker"]
        }
        
        # Process result
        processed = AnalysisService._process_feature1_result(feature1_result)
        
        # Verify None preservation
        self.assertIsNone(processed["experience_score"],
                         "experience_score should be None")
        # Verify other scores are Decimal
        self.assertIsInstance(processed["compatibility_score"], Decimal)
        self.assertIsInstance(processed["semantic_score"], Decimal)
        self.assertIsInstance(processed["skill_score"], Decimal)
        self.assertIsInstance(processed["education_score"], Decimal)
        
        # Verify values
        self.assertEqual(processed["compatibility_score"], Decimal("85.50"))
        self.assertEqual(processed["semantic_score"], Decimal("85.00"))
        self.assertEqual(processed["skill_score"], Decimal("90.00"))
    
    def test_process_feature1_result_with_none_education(self):
        """
        Test Case G Extended: Multiple None values
        
        Memverifikasi bahwa _process_feature1_result() 
        correctly mempertahankan multiple None values.
        """
        feature1_result = {
            "compatibility": {
                "score": 75.0,
                "level": "MEDIUM"
            },
            "scores": {
                "semantic": 80.0,
                "skill": 75.0,
                "experience": None,
                "education": None  # None
            },
            "skills": {
                "matched": ["Python"],
                "missing_or_not_detected": []
            },
            "recommendations": []
        }
        
        processed = AnalysisService._process_feature1_result(feature1_result)
        
        # Both None values should be preserved
        self.assertIsNone(processed["experience_score"])
        self.assertIsNone(processed["education_score"])
        
        # Other scores still Decimal
        self.assertEqual(processed["semantic_score"], Decimal("80.00"))
        self.assertEqual(processed["skill_score"], Decimal("75.00"))


# ============================================================
# REGRESSION TESTS FOR MODEL NULL HANDLING
# ============================================================

class JobMatchNullHandlingTestCase(TestCase):
    """Test bahwa JobMatch model correctly handles None values di database"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.resume = Resume.objects.create(
            user=self.user,
            original_filename="test.pdf",
            cv_file="dummy.pdf",
            extracted_text="Test CV"
        )
    
    def test_create_job_match_with_null_experience_score(self):
        """Test creating JobMatch dengan experience_score = NULL"""
        job_match = JobMatch.objects.create(
            user=self.user,
            resume=self.resume,
            job_title_target="Engineer",
            job_description_text="Test",
            compatibility_score=Decimal("75.00"),
            semantic_score=Decimal("80.00"),
            skill_score=Decimal("80.00"),
            experience_score=None,  # NULL
            education_score=Decimal("90.00"),
            compatibility_level="MEDIUM"
        )
        
        self.assertIsNone(job_match.experience_score)
        self.assertEqual(job_match.semantic_score, Decimal("80.00"))
    
    def test_create_job_match_with_null_education_score(self):
        """Test creating JobMatch dengan education_score = NULL"""
        job_match = JobMatch.objects.create(
            user=self.user,
            resume=self.resume,
            job_title_target="Engineer",
            job_description_text="Test",
            compatibility_score=Decimal("70.00"),
            semantic_score=Decimal("75.00"),
            skill_score=Decimal("70.00"),
            experience_score=Decimal("65.00"),
            education_score=None,  # NULL
            compatibility_level="MEDIUM"
        )
        
        self.assertIsNone(job_match.education_score)
        self.assertEqual(job_match.experience_score, Decimal("65.00"))
    
    def test_create_job_match_with_multiple_null_scores(self):
        """Test creating JobMatch dengan multiple NULL scores"""
        job_match = JobMatch.objects.create(
            user=self.user,
            resume=self.resume,
            job_title_target="Engineer",
            job_description_text="Test",
            compatibility_score=Decimal("75.00"),
            semantic_score=Decimal("80.00"),
            skill_score=Decimal("80.00"),
            experience_score=None,  # NULL
            education_score=None,  # NULL
            compatibility_level="MEDIUM"
        )
        
        self.assertIsNone(job_match.experience_score)
        self.assertIsNone(job_match.education_score)
        self.assertEqual(job_match.semantic_score, Decimal("80.00"))
