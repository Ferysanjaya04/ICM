
"""
Analysis Views - Feature 1: CV vs Job Requirement Matching.

Endpoints:
    POST /api/analysis/match/
    GET  /api/analysis/matches/
    GET  /api/analysis/match/<match_id>/

Alur:
    Resume milik user -> AnalysisService -> JobMatch -> JSON response.

Catatan:
    - Autentikasi wajib (JWT melalui konfigurasi DRF).
    - Tidak mengubah model AI atau formula scoring.
    - Format respons mengikuti config.api_response.
"""

import logging
import uuid

from django.db import DatabaseError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from config.api_response import success_response, error_response
from resumes.models import Resume
from recommendations.models import JobRole

from .models import JobMatch
from .services import AnalysisService


logger = logging.getLogger(__name__)

# Batasi panjang job description untuk mencegah input berlebihan.
MAX_JOB_TEXT_LENGTH = 30000
MIN_JOB_TEXT_LENGTH = 10


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _parse_uuid(value):
    """
    Konversi nilai menjadi UUID.

    Returns:
        uuid.UUID jika valid.
        None jika tidak valid.
    """
    if not isinstance(value, (str, uuid.UUID)):
        return None

    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _validate_job_text(job_text):
    """
    Validasi teks Job Requirement.

    Returns:
        (clean_text, error_message)
    """
    if not isinstance(job_text, str):
        return None, "Job Requirement harus berupa teks."

    clean_text = job_text.strip()

    if not clean_text:
        return None, "Job Requirement tidak boleh kosong."

    if len(clean_text) < MIN_JOB_TEXT_LENGTH:
        return None, (
            "Job Requirement terlalu pendek. "
            f"Minimal {MIN_JOB_TEXT_LENGTH} karakter."
        )

    if len(clean_text) > MAX_JOB_TEXT_LENGTH:
        return None, (
            "Job Requirement terlalu panjang. "
            f"Maksimal {MAX_JOB_TEXT_LENGTH} karakter."
        )

    return clean_text, None


def _internal_error():
    """
    Respons aman untuk kegagalan internal.

    Detail teknis hanya disimpan di server log.
    """
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message=(
            "Terjadi kesalahan pada server. "
            "Silakan coba kembali."
        ),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ============================================================
# POST /api/analysis/match/
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_cv_and_job(request):
    """
    Analisis CV terhadap Job Requirement.

    Request JSON:
    {
        "resume_id": "uuid",
        "job_id": "uuid"
    }

    ATAU:

    {
        "resume_id": "uuid",
        "job_text": "Deskripsi lowongan..."
    }

    Jika job_id dan job_text dikirim bersamaan,
    job_id diprioritaskan.

    Response sukses:
    {
        "status": "success",
        "data": {
            "id": "...",
            "resume_id": "...",
            "compatibility": {...},
            "scores": {...},
            "skills": {...},
            "recommendations": [...]
        }
    }
    """

    # --------------------------------------------------------
    # 1. Validasi request
    # --------------------------------------------------------

    if not isinstance(request.data, dict):
        return error_response(
            code="INVALID_REQUEST",
            message="Request body harus berupa objek JSON.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    resume_id_raw = request.data.get("resume_id")
    job_id_raw = request.data.get("job_id")
    job_text_raw = request.data.get("job_text")

    if resume_id_raw is None or resume_id_raw == "":
        return error_response(
            code="RESUME_ID_REQUIRED",
            message="resume_id wajib disediakan.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    resume_id = _parse_uuid(resume_id_raw)

    if resume_id is None:
        return error_response(
            code="INVALID_RESUME_ID",
            message="Format resume_id tidak valid. Gunakan UUID.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # 2. Ambil CV milik user yang sedang login
    # --------------------------------------------------------

    try:
        resume = Resume.objects.filter(
            id=resume_id,
            user=request.user,
        ).first()
    except DatabaseError:
        logger.exception("Gagal membaca Resume dari database.")
        return _internal_error()

    if resume is None:
        return error_response(
            code="RESUME_NOT_FOUND",
            message=(
                "Resume tidak ditemukan atau "
                "Anda tidak memiliki akses."
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )

    cv_text = resume.extracted_text

    if not isinstance(cv_text, str) or not cv_text.strip():
        return error_response(
            code="CV_TEXT_EMPTY",
            message="CV tidak memiliki teks yang dapat dianalisis.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Sesuaikan dengan validasi AnalysisService.
    if len(cv_text.strip()) < 10:
        return error_response(
            code="CV_TEXT_TOO_SHORT",
            message=(
                "Teks CV terlalu pendek untuk dianalisis. "
                "Minimal 10 karakter."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # 3. Tentukan Job Requirement
    # --------------------------------------------------------

    job_title_target = None

    if job_id_raw is not None and job_id_raw != "":
        job_id = _parse_uuid(job_id_raw)

        if job_id is None:
            return error_response(
                code="INVALID_JOB_ID",
                message="Format job_id tidak valid. Gunakan UUID.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job_role = JobRole.objects.filter(id=job_id).first()
        except DatabaseError:
            logger.exception("Gagal membaca JobRole dari database.")
            return _internal_error()

        if job_role is None:
            return error_response(
                code="JOB_ROLE_NOT_FOUND",
                message="Job Role tidak ditemukan.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        job_text_raw = job_role.description
        job_title_target = job_role.role_title

    elif job_text_raw is None:
        return error_response(
            code="JOB_REQUIREMENT_REQUIRED",
            message="job_text atau job_id wajib disediakan.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # 4. Validasi deskripsi pekerjaan
    # --------------------------------------------------------

    job_text, validation_error = _validate_job_text(
        job_text_raw
    )

    if validation_error is not None:
        return error_response(
            code="INVALID_JOB_TEXT",
            message=validation_error,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # 5. Jalankan AI Feature 1
    # --------------------------------------------------------

    try:
        analysis_result = AnalysisService.analyze_cv_vs_job(
            cv_text=cv_text,
            job_text=job_text,
            cv_filename=resume.original_filename,
        )

    except ValueError:
        logger.exception(
            "Validasi atau hasil analisis Feature 1 gagal. "
            "resume_id=%s",
            resume_id,
        )
        return error_response(
            code="ANALYSIS_INVALID",
            message=(
                "CV atau Job Requirement tidak dapat dianalisis. "
                "Periksa kembali isi dokumen."
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    except Exception:
        logger.exception(
            "AI Feature 1 gagal dijalankan. resume_id=%s",
            resume_id,
        )
        return error_response(
            code="ANALYSIS_FAILED",
            message=(
                "Proses analisis AI sedang mengalami kendala. "
                "Silakan coba kembali."
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # --------------------------------------------------------
    # 6. Pastikan hasil sesuai model database
    # --------------------------------------------------------

    if not isinstance(analysis_result, dict):
        logger.error("AnalysisService tidak mengembalikan dictionary.")
        return _internal_error()

    # JobMatch saat ini mewajibkan semantic_score dan
    # skill_score bernilai non-NULL.
    #
    # Feature 1 v2 dapat menghasilkan skill_score=None jika
    # persyaratan skill tidak terdeteksi.
    # Jangan menggantinya dengan 100 atau 0 secara paksa.
    if analysis_result.get("skill_score") is None:
        return error_response(
            code="JOB_SKILLS_UNDETERMINED",
            message=(
                "Persyaratan skill pada Job Requirement belum "
                "dapat dikenali. Tambahkan keterampilan teknis "
                "yang dibutuhkan pada deskripsi lowongan."
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if (
        analysis_result.get("compatibility_score") is None
        or analysis_result.get("semantic_score") is None
    ):
        logger.error(
            "Feature 1 menghasilkan skor wajib yang kosong. "
            "resume_id=%s",
            resume_id,
        )
        return error_response(
            code="ANALYSIS_INCOMPLETE",
            message=(
                "Hasil analisis belum lengkap dan "
                "tidak dapat disimpan."
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # --------------------------------------------------------
    # 7. Simpan hasil analisis ke PostgreSQL
    # --------------------------------------------------------

    try:
        job_match = JobMatch.objects.create(
            user=request.user,
            resume=resume,

            job_title_target=job_title_target,
            job_description_text=job_text,

            compatibility_score=analysis_result[
                "compatibility_score"
            ],
            compatibility_level=analysis_result[
                "compatibility_level"
            ],

            semantic_score=analysis_result["semantic_score"],
            skill_score=analysis_result["skill_score"],
            experience_score=analysis_result.get(
                "experience_score"
            ),
            education_score=analysis_result.get(
                "education_score"
            ),

            matched_skills=analysis_result["matched_skills"],
            missing_skills=analysis_result["missing_skills"],
            recommendations=analysis_result["recommendations"],
        )

    except Exception:
        logger.exception(
            "Gagal menyimpan JobMatch. resume_id=%s",
            resume_id,
        )
        return error_response(
            code="MATCH_SAVE_FAILED",
            message="Hasil analisis gagal disimpan.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # --------------------------------------------------------
    # 8. Format JSON response
    # --------------------------------------------------------

    try:
        response_data = AnalysisService.format_api_response(
            job_match
        )
    except Exception:
        logger.exception(
            "Gagal memformat respons JobMatch. match_id=%s",
            job_match.id,
        )
        return _internal_error()

    return success_response(
        data=response_data,
        status_code=status.HTTP_201_CREATED,
    )


# ============================================================
# GET /api/analysis/match/<match_id>/
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_match_detail(request, match_id):
    """
    Mengambil detail analisis milik user yang sedang login.
    """

    parsed_id = _parse_uuid(match_id)

    if parsed_id is None:
        return error_response(
            code="INVALID_MATCH_ID",
            message="Format match_id tidak valid.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Filter user langsung pada query agar match milik
        # user lain tidak dapat dibaca.
        job_match = (
            JobMatch.objects
            .select_related("resume")
            .filter(
                id=parsed_id,
                user=request.user,
            )
            .first()
        )

        if job_match is None:
            return error_response(
                code="MATCH_NOT_FOUND",
                message="Hasil analisis tidak ditemukan.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        response_data = AnalysisService.format_api_response(
            job_match
        )

        return success_response(
            data=response_data,
            status_code=status.HTTP_200_OK,
        )

    except Exception:
        logger.exception(
            "Gagal mengambil detail JobMatch. match_id=%s",
            parsed_id,
        )
        return _internal_error()


# ============================================================
# GET /api/analysis/matches/
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_user_matches(request):
    """
    Mengambil seluruh riwayat analisis milik user yang login.
    """

    try:
        matches = (
            JobMatch.objects
            .select_related("resume")
            .filter(user=request.user)
            .order_by("-created_at")
        )

        results = [
            AnalysisService.format_api_response(match)
            for match in matches
        ]

        return success_response(
            data={
                "count": len(results),
                "results": results,
            },
            status_code=status.HTTP_200_OK,
        )

    except Exception:
        logger.exception(
            "Gagal mengambil riwayat JobMatch. user_id=%s",
            request.user.pk,
        )
        return _internal_error()
