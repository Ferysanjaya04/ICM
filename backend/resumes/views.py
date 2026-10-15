from pathlib import Path

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import success_response, error_response
from .models import Resume
from .extraction import extract_text_from_file


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
            extracted_text = extract_text_from_file(cv_file)
        except Exception as exc:
            return error_response(
                code="EXTRACTION_FAILED",
                message="File tidak dapat diproses atau teks CV tidak ditemukan.",
                details=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        resume = Resume.objects.create(
            user=request.user,
            original_filename=original_filename,
            cv_file=cv_file,
            extracted_text=extracted_text,
        )

        return success_response(
            {
                "id": str(resume.id),
                "original_filename": resume.original_filename,
                "extracted_text": resume.extracted_text,
                "uploaded_at": resume.uploaded_at.isoformat(),
            },
            status_code=status.HTTP_201_CREATED,
        )