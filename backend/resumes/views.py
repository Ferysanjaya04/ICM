from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import success_response, error_response
from .models import Resume
from .extraction import extract_document, ExtractionQualityError


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class ResumeUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        cv_file = request.FILES.get("cv_file")

        if not cv_file:
            return error_response(
                code="FILE_REQUIRED",
                message="File CV wajib diunggah.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        original_filename = Path(cv_file.name).name
        extension = Path(original_filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            return error_response(
                code="INVALID_FILE_TYPE",
                message="Format file harus PDF atau DOCX.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if cv_file.size == 0:
            return error_response(
                code="EMPTY_FILE",
                message="File CV tidak boleh kosong.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if cv_file.size > MAX_FILE_SIZE:
            return error_response(
                code="FILE_TOO_LARGE",
                message="Ukuran file maksimal 10 MB.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            extraction = extract_document(cv_file)
            extracted_text = extraction["text"]
        except Exception as exc:
            return error_response(
                code="EXTRACTION_FAILED",
                message="File tidak dapat diproses atau teks CV tidak ditemukan.",
                details={'extraction_quality': exc.quality} if isinstance(exc, ExtractionQualityError) else None,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        resume = Resume.objects.create(
            user=request.user,
            original_filename=original_filename,
            cv_file=cv_file,
            extracted_text=extracted_text,
            parsed_sections={"extraction_quality": extraction["quality"]},
        )

        return success_response(
            {
                "id": str(resume.id),
                "original_filename": resume.original_filename,
                "extracted_text": resume.extracted_text,
                "extraction_quality": resume.extraction_quality,
                "uploaded_at": resume.uploaded_at.isoformat(),
            },
            status_code=status.HTTP_201_CREATED,
        )

class ResumeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        resumes = (
            Resume.objects
            .filter(user=request.user)
            .order_by("-uploaded_at")
        )

        data = [
            {
                "id": str(resume.id),
                "original_filename": resume.original_filename,
                "uploaded_at": resume.uploaded_at.isoformat(),
                "extraction_quality": resume.extraction_quality,
                "has_extracted_text": bool(
                    resume.extracted_text.strip()
                ),
            }
            for resume in resumes
        ]

        return success_response({
            "count": len(data),
            "resumes": data,
        })


class ResumeDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, resume_id):
        # 404 also hides whether a document owned by another account exists.
        resume = Resume.objects.filter(id=resume_id, user=request.user).first()
        if resume is None or not resume.cv_file:
            return self._not_found()
        try:
            document = resume.cv_file.open("rb")
        except (OSError, ValueError, SuspiciousFileOperation):
            return self._not_found()
        filename = Path(resume.original_filename.replace("\\", "/")).name
        filename = "".join(character for character in filename if character.isprintable())
        response = FileResponse(
            document, as_attachment=True,
            filename=filename or "resume", content_type="application/octet-stream",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @staticmethod
    def _not_found():
        return error_response(
            code="RESUME_NOT_FOUND",
            message="Dokumen CV tidak ditemukan atau Anda tidak memiliki akses.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
