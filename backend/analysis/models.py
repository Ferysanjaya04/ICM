import uuid

from django.db import models
from django.contrib.auth.models import User

from resumes.models import Resume


class JobMatch(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_matches"
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="matches"
    )

    job_title_target = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    job_file = models.FileField(
        upload_to="job_requirements_pdf/",
        null=True,
        blank=True
    )

    job_description_text = models.TextField()

    # Compatibility Scores
    compatibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    semantic_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    skill_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    experience_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    education_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    compatibility_level = models.CharField(
        max_length=50
    )

    # Matching Results
    matched_skills = models.JSONField(
        default=list
    )

    missing_skills = models.JSONField(
        default=list
    )

    recommendations = models.JSONField(
        default=list
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Match {self.compatibility_score}% - "
            f"{self.resume.original_filename}"
        )