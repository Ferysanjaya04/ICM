import uuid

from django.db import models
from django.contrib.auth.models import User

from resumes.models import Resume


class CareerRecommendation(models.Model):
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
        related_name="recommendations"
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="career_profiles"
    )

    dominant_category = models.CharField(
        max_length=100
    )

    profile_summary = models.JSONField(
        default=dict
    )

    detected_skills = models.JSONField(
        default=dict
    )

    learning_path = models.JSONField(
        default=dict
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Career Blueprint - {self.dominant_category} "
            f"({self.created_at.strftime('%Y-%m-%d')})"
        )


class TopRole(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    recommendation = models.ForeignKey(
        CareerRecommendation,
        on_delete=models.CASCADE,
        related_name="top_roles"
    )

    role_title = models.CharField(
        max_length=255
    )

    match_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    rank = models.PositiveSmallIntegerField()

    salary_range = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    category = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["rank"]

    def __str__(self):
        return (
            f"Rank {self.rank}: {self.role_title} "
            f"({self.match_percentage}%)"
        )