
"""
Analysis Service - Feature 1: CV vs Job Matching Engine

Tanggung jawab:
1. Memvalidasi teks CV dan Job Requirement.
2. Memuat skills database menggunakan Django cache.
3. Mengelola SentenceTransformer melalui singleton.
4. Menjalankan pipeline Feature 1.
5. Mengubah hasil ke format yang kompatibel dengan Django.
6. Mencatat ID analisis, fingerprint input, durasi, skor, dan error.
"""

import hashlib
import logging
import threading
import time
import uuid

from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

from django.core.cache import cache

from lib.feature1 import analyze_cv_job, load_skills_database


logger = logging.getLogger(__name__)


# ============================================================
# MODEL MANAGER
# ============================================================

class _ModelManager:
    """
    Singleton manager untuk SentenceTransformer.

    Model dimuat secara lazy saat pertama kali dibutuhkan.
    Instance model digunakan kembali selama proses Django berjalan.
    """

    _instance = None
    _model = None
    _load_error = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)

        return cls._instance

    @property
    def model(self):
        """Mengembalikan model yang tersedia atau memuatnya dahulu."""

        if self._model is None and self._load_error is None:
            with self._lock:
                if self._model is None and self._load_error is None:
                    self._load_model()

        if self._load_error is not None:
            raise RuntimeError(
                "Gagal memuat SentenceTransformer: "
                f"{self._load_error}"
            )

        return self._model

    def _load_model(self):
        """Memuat model satu kali secara thread-safe."""

        start_time = time.perf_counter()
        model_name = "all-MiniLM-L6-v2"

        logger.info(
            "[Feature 1][Model] Memulai pemuatan model: %s",
            model_name,
        )

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)

            elapsed = time.perf_counter() - start_time

            logger.info(
                "[Feature 1][Model] Model berhasil dimuat | "
                "Model=%s | Durasi=%.3f detik",
                model_name,
                elapsed,
            )

        except Exception as exc:
            self._load_error = str(exc)

            logger.exception(
                "[Feature 1][Model] Pemuatan model gagal"
            )

            raise RuntimeError(
                f"Gagal memuat model {model_name}: {exc}"
            ) from exc


# ============================================================
# ANALYSIS SERVICE
# ============================================================

class AnalysisService:
    """Service untuk analisis kecocokan CV terhadap Job Requirement."""

    SKILLS_DB_CACHE_KEY = "vitlog_skills_database"
    SKILLS_DB_CACHE_TIMEOUT = 3600

    _model_manager = None
    _manager_lock = threading.Lock()

    # --------------------------------------------------------
    # MODEL MANAGER
    # --------------------------------------------------------

    @classmethod
    def _get_model_manager(cls):
        """Mengambil instance model manager."""

        if cls._model_manager is None:
            with cls._manager_lock:
                if cls._model_manager is None:
                    cls._model_manager = _ModelManager()

        return cls._model_manager

    # --------------------------------------------------------
    # UTILITAS LOGGING
    # --------------------------------------------------------

    @staticmethod
    def _fingerprint(value: str) -> str:
        """
        Membuat sidik jari teks untuk membandingkan input.

        Isi CV dan Job Requirement tidak dicetak ke log.
        Fingerprint bukan pengganti validasi atau autentikasi.
        """

        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:12]

    @staticmethod
    def _elapsed(start_time: float) -> float:
        """Mengembalikan durasi dalam detik."""

        return time.perf_counter() - start_time

    # --------------------------------------------------------
    # SKILLS DATABASE
    # --------------------------------------------------------

    @staticmethod
    def get_skills_database():
        """
        Memuat skills database melalui Django cache.

        Cache hanya menyimpan database skill, bukan hasil analisis CV.
        """

        start_time = time.perf_counter()

        cached_db = cache.get(
            AnalysisService.SKILLS_DB_CACHE_KEY
        )

        if cached_db is not None:
            logger.info(
                "[Feature 1][Skills DB] Menggunakan database dari cache"
            )
            return cached_db

        db_path = (
            Path(__file__).resolve().parent.parent
            / "lib"
            / "skills_database.json"
        )

        if not db_path.is_file():
            logger.error(
                "[Feature 1][Skills DB] File tidak ditemukan: %s",
                db_path,
            )
            raise FileNotFoundError(
                f"Skills database tidak ditemukan: {db_path}"
            )

        logger.info(
            "[Feature 1][Skills DB] Memuat database dari file: %s",
            db_path,
        )

        skills_db = load_skills_database(str(db_path))

        if skills_db is None:
            raise ValueError(
                "Skills database tidak menghasilkan data yang valid"
            )

        cache.set(
            AnalysisService.SKILLS_DB_CACHE_KEY,
            skills_db,
            AnalysisService.SKILLS_DB_CACHE_TIMEOUT,
        )

        logger.info(
            "[Feature 1][Skills DB] Database berhasil dimuat | "
            "Durasi=%.3f detik",
            AnalysisService._elapsed(start_time),
        )

        return skills_db

    # --------------------------------------------------------
    # MAIN ANALYSIS PIPELINE
    # --------------------------------------------------------

    @staticmethod
    def analyze_cv_vs_job(
        cv_text: str,
        job_text: str,
        cv_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Menjalankan analisis CV terhadap Job Requirement.

        Setiap pemanggilan menjalankan analyze_cv_job() dengan input
        yang diberikan. Hasil analisis tidak di-cache oleh service ini.

        Args:
            cv_text: Teks CV hasil ekstraksi.
            job_text: Teks Job Requirement.
            cv_filename: Nama file CV untuk logging.

        Returns:
            Dictionary hasil yang kompatibel dengan views.py.

        Raises:
            ValueError: Jika input tidak valid.
            FileNotFoundError: Jika skills database tidak tersedia.
            RuntimeError: Jika model AI gagal dimuat.
            Exception: Jika pipeline analisis gagal.
        """

        total_start = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        filename = cv_filename or "unknown"

        cv_length = len(cv_text) if isinstance(cv_text, str) else 0
        job_length = len(job_text) if isinstance(job_text, str) else 0

        cv_fingerprint = (
            AnalysisService._fingerprint(cv_text)
            if isinstance(cv_text, str)
            else "invalid"
        )

        job_fingerprint = (
            AnalysisService._fingerprint(job_text)
            if isinstance(job_text, str)
            else "invalid"
        )

        logger.info(
            "[Feature 1][%s] Analisis dimulai | "
            "CV=%s | CV chars=%d | Job chars=%d | "
            "CV fingerprint=%s | Job fingerprint=%s",
            request_id,
            filename,
            cv_length,
            job_length,
            cv_fingerprint,
            job_fingerprint,
        )

        try:
            # 1. Validasi input
            validation_start = time.perf_counter()

            if not isinstance(cv_text, str) or not cv_text.strip():
                raise ValueError(
                    "CV text tidak boleh kosong dan harus berupa string"
                )

            if not isinstance(job_text, str) or not job_text.strip():
                raise ValueError(
                    "Job text tidak boleh kosong dan harus berupa string"
                )

            if len(cv_text.strip()) < 10:
                raise ValueError(
                    "CV text terlalu pendek (minimal 10 karakter)"
                )

            if len(job_text.strip()) < 10:
                raise ValueError(
                    "Job text terlalu pendek (minimal 10 karakter)"
                )

            logger.info(
                "[Feature 1][%s][Validation] Validasi selesai | "
                "Durasi=%.3f detik",
                request_id,
                AnalysisService._elapsed(validation_start),
            )

            # 2. Muat skills database
            skills_start = time.perf_counter()

            skills_db = AnalysisService.get_skills_database()

            logger.info(
                "[Feature 1][%s][Skills DB] Tahap selesai | "
                "Durasi=%.3f detik",
                request_id,
                AnalysisService._elapsed(skills_start),
            )

            # 3. Ambil model manager
            manager_start = time.perf_counter()

            model_manager = AnalysisService._get_model_manager()

            logger.info(
                "[Feature 1][%s][Model Manager] Manager siap | "
                "Durasi=%.3f detik",
                request_id,
                AnalysisService._elapsed(manager_start),
            )

            # 4. Jalankan pipeline Feature 1
            pipeline_start = time.perf_counter()

            logger.info(
                "[Feature 1][%s][Pipeline] "
                "Memanggil analyze_cv_job()",
                request_id,
            )

            result = analyze_cv_job(
                cv_text=cv_text,
                job_text=job_text,
                cv_filename=cv_filename,
                skills_db_path=None,
                model_manager=model_manager,
            )

            pipeline_duration = AnalysisService._elapsed(
                pipeline_start
            )

            logger.info(
                "[Feature 1][%s][Pipeline] analyze_cv_job() selesai | "
                "Durasi=%.3f detik",
                request_id,
                pipeline_duration,
            )

            if not isinstance(result, dict):
                raise TypeError(
                    "Feature 1 harus menghasilkan dictionary"
                )

            # 5. Proses hasil agar kompatibel dengan Django
            processing_start = time.perf_counter()

            processed_result = (
                AnalysisService._process_feature1_result(result)
            )

            logger.info(
                "[Feature 1][%s][Result] Pemrosesan hasil selesai | "
                "Durasi=%.3f detik",
                request_id,
                AnalysisService._elapsed(processing_start),
            )

            # 6. Catat ringkasan skor
            compatibility = result.get("compatibility") or {}
            scores = result.get("scores") or {}
            skills = result.get("skills") or {}

            matched_skills = skills.get("matched") or []
            missing_skills = (
                skills.get("missing_or_not_detected") or []
            )

            logger.info(
                "[Feature 1][%s][Result] Skor=%s | Level=%s | "
                "Semantic=%s | Skill=%s | Experience=%s | "
                "Education=%s | Matched=%d | Missing=%d",
                request_id,
                compatibility.get("score"),
                compatibility.get("level"),
                scores.get("semantic"),
                scores.get("skill"),
                scores.get("experience"),
                scores.get("education"),
                len(matched_skills),
                len(missing_skills),
            )

            logger.info(
                "[Feature 1][%s] Analisis berhasil | "
                "CV=%s | Pipeline=%.3f detik | Total=%.3f detik",
                request_id,
                filename,
                pipeline_duration,
                AnalysisService._elapsed(total_start),
            )

            return processed_result

        except Exception:
            logger.exception(
                "[Feature 1][%s] Analisis gagal | "
                "CV=%s | Durasi sebelum gagal=%.3f detik",
                request_id,
                filename,
                AnalysisService._elapsed(total_start),
            )
            raise

    # --------------------------------------------------------
    # RESULT PROCESSING
    # --------------------------------------------------------

    @staticmethod
    def _process_feature1_result(
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Mengubah hasil Feature 1 ke format yang digunakan Django.

        Nilai None tetap dipertahankan untuk skor yang tidak tersedia.
        """

        def to_decimal(value):
            if value is None:
                return None

            try:
                return Decimal(str(round(float(value), 2)))
            except (TypeError, ValueError, ArithmeticError) as exc:
                raise ValueError(
                    f"Nilai skor tidak valid: {value!r}"
                ) from exc

        try:
            compatibility = result["compatibility"]
            scores = result["scores"]
            skills = result["skills"]
            recommendations = result["recommendations"]

            if not isinstance(compatibility, dict):
                raise TypeError("'compatibility' harus berupa dictionary")

            if not isinstance(scores, dict):
                raise TypeError("'scores' harus berupa dictionary")

            if not isinstance(skills, dict):
                raise TypeError("'skills' harus berupa dictionary")

            matched_skills = skills["matched"]
            missing_skills = skills["missing_or_not_detected"]

            if not isinstance(matched_skills, list):
                raise TypeError("'skills.matched' harus berupa list")

            if not isinstance(missing_skills, list):
                raise TypeError(
                    "'skills.missing_or_not_detected' harus berupa list"
                )

            if not isinstance(recommendations, list):
                raise TypeError("'recommendations' harus berupa list")

            compatibility_score = to_decimal(
                compatibility["score"]
            )

            if compatibility_score is None:
                raise ValueError(
                    "Skor compatibility tidak boleh None"
                )

            compatibility_level = compatibility["level"]

            if not isinstance(compatibility_level, str):
                raise TypeError(
                    "Level compatibility harus berupa string"
                )

            return {
                "compatibility_score": compatibility_score,
                "compatibility_level": compatibility_level,

                "semantic_score": to_decimal(
                    scores.get("semantic")
                ),
                "skill_score": to_decimal(
                    scores.get("skill")
                ),
                "experience_score": to_decimal(
                    scores.get("experience")
                ),
                "education_score": to_decimal(
                    scores.get("education")
                ),

                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "recommendations": recommendations,

                # Mempertahankan kompatibilitas kode sebelumnya.
                "_raw_result": result,
            }

        except (KeyError, TypeError, ValueError) as exc:
            logger.exception(
                "[Feature 1][Result] Format hasil Feature 1 tidak valid"
            )
            raise ValueError(
                f"Format hasil Feature 1 tidak valid: {exc}"
            ) from exc

    # --------------------------------------------------------
    # API RESPONSE FORMATTER
    # --------------------------------------------------------

    @staticmethod
    def format_api_response(job_match) -> Dict[str, Any]:
        """
        Mengubah JobMatch menjadi respons API.

        Struktur response dipertahankan agar kompatibel dengan frontend.
        """

        job_description = job_match.job_description_text or ""
        matched_skills = job_match.matched_skills or []
        missing_skills = job_match.missing_skills or []

        return {
            "id": str(job_match.id),
            "resume_id": str(job_match.resume.id),
            "resume_filename": job_match.resume.original_filename,
            "job_title_target": job_match.job_title_target,

            "job_description": (
                job_description[:200] + "..."
                if len(job_description) > 200
                else job_description
            ),

            "compatibility": {
                "score": (
                    float(job_match.compatibility_score)
                    if job_match.compatibility_score is not None
                    else None
                ),
                "level": job_match.compatibility_level,
            },

            "scores": {
                "semantic": (
                    float(job_match.semantic_score)
                    if job_match.semantic_score is not None
                    else None
                ),
                "skill": (
                    float(job_match.skill_score)
                    if job_match.skill_score is not None
                    else None
                ),
                "experience": (
                    float(job_match.experience_score)
                    if job_match.experience_score is not None
                    else None
                ),
                "education": (
                    float(job_match.education_score)
                    if job_match.education_score is not None
                    else None
                ),
            },

            "skills": {
                "matched": matched_skills,
                "missing": missing_skills,
                "matched_count": len(matched_skills),
                "missing_count": len(missing_skills),
            },

            "recommendations": job_match.recommendations or [],
            "created_at": (
                job_match.created_at.isoformat()
                if job_match.created_at
                else None
            ),
        }
