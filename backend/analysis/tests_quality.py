
"""
Evaluasi kualitas AI Feature 1 ICM.

Menggunakan model SentenceTransformer asli untuk memeriksa
apakah lowongan yang relevan memperoleh skor lebih tinggi
dibandingkan lowongan yang tidak relevan.
"""

from django.test import SimpleTestCase

from analysis.services import AnalysisService


class Feature1QualityTests(SimpleTestCase):

    CV_BACKEND = """
    Backend Software Developer.
    Pendidikan S1 Teknik Informatika.
    Pengalaman kerja 3 tahun sebagai Backend Developer.
    Mengembangkan REST API dengan Python, Django,
    PostgreSQL, Docker, Redis, dan Git.
    """

    JOB_BACKEND = """
    Lowongan Backend Developer.
    Pendidikan minimal S1 Teknik Informatika.
    Minimal 2 tahun pengalaman kerja.
    Wajib menguasai Python, Django, PostgreSQL,
    Docker, dan REST API.
    """

    JOB_DESIGNER = """
    Lowongan UI UX Designer.
    Pendidikan minimal S1 Desain.
    Minimal 2 tahun pengalaman kerja.
    Wajib menguasai Figma, Adobe Photoshop,
    wireframing, prototyping, dan user research.
    """

    def test_relevant_job_scores_higher(self):
        backend_result = AnalysisService.analyze_cv_vs_job(
            cv_text=self.CV_BACKEND,
            job_text=self.JOB_BACKEND,
        )

        designer_result = AnalysisService.analyze_cv_vs_job(
            cv_text=self.CV_BACKEND,
            job_text=self.JOB_DESIGNER,
        )

        backend_score = float(
            backend_result["compatibility_score"]
        )

        designer_score = float(
            designer_result["compatibility_score"]
        )

        print(
            "\nQUALITY EVALUATION FEATURE 1"
            f"\nBackend CV vs Backend Job : {backend_score:.2f}%"
            f"\nBackend CV vs Designer Job: {designer_score:.2f}%"
        )

        self.assertGreater(
            backend_score,
            designer_score,
            "CV Backend seharusnya lebih cocok dengan "
            "lowongan Backend dibanding UI/UX Designer.",
        )

    def test_missing_skills_detected(self):
        result = AnalysisService.analyze_cv_vs_job(
            cv_text=self.CV_BACKEND,
            job_text=self.JOB_BACKEND + (
                " Selain itu membutuhkan Kubernetes."
            ),
        )

        missing_skills = [
            skill.lower()
            for skill in result["missing_skills"]
        ]

        self.assertIn(
            "kubernetes",
            missing_skills,
            "Kubernetes seharusnya terdeteksi sebagai skill gap.",
        )
