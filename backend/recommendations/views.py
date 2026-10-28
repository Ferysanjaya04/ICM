import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from resumes.models import Resume
from .models import CareerRecommendation, TopRole, JobRole
from .serializers import (
    CareerRecommendationSerializer,
    CareerRecommendationListSerializer,
    TopRoleSerializer,
    JobRoleSerializer
)
from lib.feature2 import recommend_career, validate_cv_text

logger = logging.getLogger(__name__)


class CareerRecommendationViewSet(viewsets.ModelViewSet):
    """
    ViewSet untuk Career Recommendation (Feature 2).
    
    Endpoints:
    - POST /api/recommendations/generate/ - Generate recommendations dari resume
    - GET /api/recommendations/ - List user's recommendations
    - GET /api/recommendations/<id>/ - Get recommendation detail
    - DELETE /api/recommendations/<id>/ - Delete recommendation
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = CareerRecommendationSerializer
    
    def get_queryset(self):
        """Filter recommendations untuk user yang sedang login."""
        return CareerRecommendation.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Gunakan serializer yang lebih sederhana untuk list view."""
        if self.action == 'list':
            return CareerRecommendationListSerializer
        return CareerRecommendationSerializer
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate career recommendations dari resume user.
        
        Request body:
        {
            "resume_id": "uuid" (optional - jika tidak ada, pakai resume terakhir)
        }
        
        Response:
        {
            "id": "uuid",
            "resume": "uuid",
            "dominant_category": str,
            "top_recommendations": [...],
            "detected_skills": [...],
            "profile_summary": {...}
        }
        """
        try:
            # Get resume dari request atau gunakan yang terakhir
            resume_id = request.data.get('resume_id')
            
            if resume_id:
                resume = get_object_or_404(Resume, id=resume_id, user=request.user)
            else:
                # Get latest resume untuk user
                resume = Resume.objects.filter(user=request.user).latest('uploaded_at')
                if not resume:
                    return Response(
                        {
                            "status": "error",
                            "error": "Tidak ada CV yang diunggah. Silakan upload CV terlebih dahulu."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate CV text
            if not resume.extracted_text:
                return Response(
                    {
                        "status": "error",
                        "error": "CV text tidak dapat diekstrak dari file yang diunggah."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            is_valid, validation_msg = validate_cv_text(resume.extracted_text)
            if not is_valid:
                return Response(
                    {
                        "status": "error",
                        "error": validation_msg
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call Feature 2 AI engine
            logger.info(f"Generating recommendations untuk resume: {resume.id}")
            recommendation_result = recommend_career(resume.extracted_text)
            
            # Check if AI processing failed
            if recommendation_result.get("status") in ["error"]:
                return Response(
                    {
                        "status": "error",
                        "error": recommendation_result.get("error", "AI processing failed")
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create CareerRecommendation record
            predicted_category = recommendation_result.get("predicted_category", "Unknown")
            profile_summary = recommendation_result.get("profile_summary", {})
            detected_skills = recommendation_result.get("detected_skills", [])
            top_recommendations = recommendation_result.get("top_recommendations", [])
            
            # Cek apakah sudah ada recommendation untuk resume ini
            existing = CareerRecommendation.objects.filter(resume=resume).first()
            if existing:
                # Update existing recommendation
                existing.dominant_category = predicted_category
                existing.profile_summary = profile_summary
                existing.detected_skills = detected_skills
                existing.save()
                career_rec = existing
            else:
                # Create baru
                career_rec = CareerRecommendation.objects.create(
                    user=request.user,
                    resume=resume,
                    dominant_category=predicted_category,
                    profile_summary=profile_summary,
                    detected_skills=detected_skills
                )
            
            # Create TopRole records
            TopRole.objects.filter(recommendation=career_rec).delete()
            for rec_data in top_recommendations:
                TopRole.objects.create(
                    recommendation=career_rec,
                    role_title=rec_data.get('role_title', 'Unknown'),
                    match_percentage=rec_data.get('match_percentage', 0),
                    rank=rec_data.get('rank', 0),
                    salary_range=rec_data.get('salary_range', ''),
                    category=rec_data.get('category', '')
                )
            
            # Return recommendation dengan top roles
            serializer = CareerRecommendationSerializer(career_rec)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Resume.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "error": "CV tidak ditemukan atau tidak milik Anda."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return Response(
                {
                    "status": "error",
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request, *args, **kwargs):
        """List semua recommendations user."""
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Get detail recommendation."""
        return super().retrieve(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete recommendation."""
        return super().destroy(request, *args, **kwargs)


class JobRoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet untuk Job Role reference data (read-only).
    
    Endpoints:
    - GET /api/job-roles/ - List all job roles
    - GET /api/job-roles/<id>/ - Get job role detail
    """
    
    queryset = JobRole.objects.all()
    serializer_class = JobRoleSerializer
    permission_classes = [IsAuthenticated]  # Require auth untuk akses
