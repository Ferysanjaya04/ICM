import uuid

from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resumes"
    )

    original_filename = models.CharField(max_length=255)

    cv_file = models.FileField(
        upload_to="resumes_pdf/"
    )

    extracted_text = models.TextField()

    parsed_sections = models.JSONField(
        default=dict,
        blank=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.original_filename} ({self.uploaded_at.strftime('%Y-%m-%d')})"