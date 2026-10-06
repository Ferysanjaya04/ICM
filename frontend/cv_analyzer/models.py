from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    def __str__(self):
        return self.username

class AnalysisLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='analyses')
    cv_file = models.CharField(max_length=255)
    job_description = models.TextField()
    target_role = models.CharField(max_length=100, blank=True, null=True)
    results = models.JSONField()
    mode = models.CharField(max_length=10, choices=[('match', 'CV vs Job Matching'), ('career', 'Career Recommendation')])
    compatibility_score = models.FloatField(default=0)
    compatibility_level = models.CharField(max_length=20, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('EXCELLENT', 'Excellent')])
    top_roles = models.JSONField(default=list)
    skill_gap_matched = models.JSONField(default=list)
    skill_gap_missing = models.JSONField(default=list)
    roadmap = models.JSONField(default=list)
    processing_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.mode} - {self.created_at}"