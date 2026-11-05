
import logging
from uuid import UUID

from django.db import models, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from resumes.models import Resume
from .models import CareerRecommendation, TopRole, JobRole
from .serializers import (
    CareerRecommendationSerializer,
    CareerRecommendationListSerializer,
    JobRoleSerializer,
)
from lib.feature2 import recommend_career, validate_cv_text


logger = logging.getLogger(__name__)


def error_response(message, http_status):
    return Response(
        {
            "status": "error",
            "error": message,
        },
        status=http_status,
    )


class CareerRecommendationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Feature 2: Career Recommendation.

    GET    /api/recommendations/
    GET    /api/recommendations/<id>/
    DELETE /api/recommendations/<id>/
    POST   /api/recommendations/generate/

    POST generate memerlukan autentikasi.
    Hasil rekomendasi hanya dapat diakses pemiliknya.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CareerRecommendationSerializer

    def get_queryset(self):
        return (
            CareerRecommendation.objects
            .filter(user=self.request.user)
            .select_related("resume")
            .prefetch_related("top_roles")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CareerRecommendationListSerializer

        return CareerRecommendationSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """
        Body:
        {
            "resume_id": "uuid"
        }

        Jika resume_id tidak diberikan,
        gunakan CV terbaru milik pengguna.
        """

        resume_id = request.data.get("resume_id")

        # 1. Validasi resume_id jika diberikan.
        if resume_id is not None:
            try:
                normalized_id = str(UUID(str(resume_id)))
            except (ValueError, TypeError, AttributeError):
                return error_response(
                    "resume_id harus berupa UUID yang valid.",
                    status.HTTP_400_BAD_REQUEST,
                )

            resume = (
                Resume.objects
                .filter(
                    id=normalized_id,
                    user=request.user,
                )
                .first()
            )

            if resume is None:
                return error_response(
                    "CV tidak ditemukan atau bukan milik Anda.",
                    status.HTTP_404_NOT_FOUND,
                )

        else:
            resume = (
                Resume.objects
                .filter(user=request.user)
                .order_by("-uploaded_at", "-pk")
                .first()
            )

            if resume is None:
                return error_response(
                    "Belum ada CV. Silakan upload CV terlebih dahulu.",
                    status.HTTP_400_BAD_REQUEST,
                )

        # 2. Validasi teks CV.
        cv_text = resume.extracted_text or ""

        is_valid, validation_message = validate_cv_text(
            cv_text
        )

        if not is_valid:
            return error_response(
                validation_message,
                status.HTTP_400_BAD_REQUEST,
            )

        # 3. Jalankan AI Feature 2.
        try:
            logger.info(
                "Memulai Feature 2 | resume_id=%s",
                resume.id,
            )

            ai_result = recommend_career(cv_text)

        except Exception:
            logger.exception(
                "Feature 2 mengalami error | resume_id=%s",
                resume.id,
            )

            return error_response(
                "Layanan rekomendasi karier sedang mengalami masalah.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if (
            not isinstance(ai_result, dict)
            or ai_result.get("status") != "success"
        ):
            logger.error(
                "Feature 2 gagal | resume_id=%s | status=%s",
                resume.id,
                ai_result.get("status")
                if isinstance(ai_result, dict)
                else "invalid_result",
            )

            return error_response(
                "Rekomendasi karier belum berhasil dihasilkan.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        top_recommendations = ai_result.get(
            "top_recommendations", []
        )

        # 4. Jangan simpan rekomendasi yang tidak lengkap.
        if (
            not isinstance(top_recommendations, list)
            or len(top_recommendations) != 3
        ):
            logger.error(
                "Top-3 tidak lengkap | resume_id=%s",
                resume.id,
            )

            return error_response(
                "AI belum menghasilkan tiga rekomendasi karier.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        expected_ranks = [1, 2, 3]

        try:
            ranks = [
                item["rank"]
                for item in top_recommendations
            ]

            titles = [
                str(item["role_title"]).strip()
                for item in top_recommendations
            ]

        except (KeyError, TypeError, ValueError):
            return error_response(
                "Format hasil rekomendasi AI tidak valid.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if (
            ranks != expected_ranks
            or not all(titles)
            or len(set(titles)) != 3
        ):
            return error_response(
                "Hasil rekomendasi AI tidak lengkap atau duplikat.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        dominant_category = ai_result.get(
            "predicted_category"
        )

        profile_summary = ai_result.get(
            "profile_summary", {}
        )

        detected_skills = ai_result.get(
            "detected_skills", []
        )

        learning_path = ai_result.get(
            "learning_path", []
        )

        if (
            not dominant_category
            or not isinstance(profile_summary, dict)
            or not isinstance(detected_skills, list)
            or not isinstance(learning_path, list)
        ):
            return error_response(
                "Metadata rekomendasi AI tidak valid.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Pastikan model memiliki kolom learning_path.
        try:
            learning_path_field = (
                CareerRecommendation._meta.get_field(
                    "learning_path"
                )
            )
        except Exception:
            logger.exception(
                "Kolom learning_path tidak ditemukan."
            )

            return error_response(
                "Konfigurasi penyimpanan rekomendasi belum lengkap.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Bila learning_path merupakan TextField,
        # simpan sebagai JSON string.
        if isinstance(learning_path_field, models.JSONField):
            stored_learning_path = learning_path
        else:
            import json
            stored_learning_path = json.dumps(
                learning_path,
                ensure_ascii=False,
            )

        # 5. Simpan seluruh data secara atomik.
        try:
            with transaction.atomic():
                career_rec = (
                    CareerRecommendation.objects
                    .select_for_update()
                    .filter(
                        user=request.user,
                        resume=resume,
                    )
                    .first()
                )

                created = career_rec is None

                if created:
                    career_rec = CareerRecommendation(
                        user=request.user,
                        resume=resume,
                    )

                career_rec.dominant_category = (
                    dominant_category
                )
                career_rec.profile_summary = (
                    profile_summary
                )
                career_rec.detected_skills = (
                    detected_skills
                )
                career_rec.learning_path = (
                    stored_learning_path
                )

                career_rec.save()

                # Hapus TopRole lama hanya setelah
                # hasil AI tervalidasi.
                TopRole.objects.filter(
                    recommendation=career_rec
                ).delete()

                for item in top_recommendations:
                    TopRole.objects.create(
                        recommendation=career_rec,
                        role_title=str(
                            item["role_title"]
                        ),
                        category=str(
                            item.get("category") or ""
                        ),
                        match_percentage=(
                            item.get(
                                "match_percentage", 0
                            )
                        ),
                        rank=item["rank"],
                        salary_range=str(
                            item.get("salary_range") or ""
                        ),
                    )

        except Exception:
            logger.exception(
                "Gagal menyimpan rekomendasi | resume_id=%s",
                resume.id,
            )

            return error_response(
                "Gagal menyimpan rekomendasi ke database.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 6. Respons menggunakan serializer lama
        # agar kompatibilitas frontend tetap terjaga.
        serializer = CareerRecommendationSerializer(
            career_rec
        )

        logger.info(
            "Feature 2 selesai | resume_id=%s | recommendation_id=%s",
            resume.id,
            career_rec.id,
        )

        return Response(
            serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class JobRoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/job-roles/
    GET /api/job-roles/<id>/
    """

    queryset = JobRole.objects.all().order_by(
        "role_title"
    )
    serializer_class = JobRoleSerializer
    permission_classes = [IsAuthenticated]
