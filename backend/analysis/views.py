"""
Analysis Views - API endpoints untuk CV-Job Requirement matching
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from resumes.models import Resume
from recommendations.models import JobRole
from .models import JobMatch
from .services import AnalysisService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_cv_and_job(request):
    """
    POST /api/analysis/match/
    
    Analisis CV terhadap Job Requirement.
    
    Request body:
    {
        "resume_id": "uuid",
        "job_id": "uuid" (optional - if provided, gunakan JobRole.description)
        "job_text": "string" (optional - if job_id tidak ada, gunakan text ini)
    }
    
    Response:
    {
        "id": "uuid",
        "resume_id": "uuid",
        "compatibility": {"score": 70.99, "level": "MEDIUM"},
        "scores": {...},
        "matched_skills": [...],
        "missing_skills": [...],
        "recommendations": [...]
    }
    """
    
    try:
        # 1. Validasi request
        resume_id = request.data.get('resume_id')
        job_id = request.data.get('job_id')
        job_text = request.data.get('job_text')
        
        if not resume_id:
            return Response(
                {"error": "resume_id wajib disediakan"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Ambil Resume - pastikan milik user yang request
        try:
            resume = Resume.objects.get(id=resume_id, user=request.user)
        except Resume.DoesNotExist:
            return Response(
                {"error": "Resume tidak ditemukan atau Anda tidak memiliki akses"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3. Validasi CV text tersedia
        cv_text = resume.extracted_text
        if not cv_text or not cv_text.strip():
            return Response(
                {"error": "CV tidak memiliki teks yang dapat diekstrak"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 4. Dapatkan job_text - dari job_id atau input langsung
        job_title_target = None
        if job_id:
            try:
                job_role = JobRole.objects.get(id=job_id)
                job_text = job_role.description
                job_title_target = job_role.role_title
            except JobRole.DoesNotExist:
                return Response(
                    {"error": "Job Role tidak ditemukan"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        if not job_text or not job_text.strip():
            return Response(
                {"error": "job_text atau job_id wajib disediakan"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. Jalankan analisis
        try:
            analysis_result = AnalysisService.analyze_cv_vs_job(
                cv_text=cv_text,
                job_text=job_text,
                cv_filename=resume.original_filename
            )
        except ValueError as e:
            return Response(
                {"error": f"Analisis gagal: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error internal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 6. Simpan ke database
        try:
            job_match = JobMatch.objects.create(
                user=request.user,
                resume=resume,
                job_title_target=job_title_target,
                job_description_text=job_text,
                
                compatibility_score=analysis_result["compatibility_score"],
                compatibility_level=analysis_result["compatibility_level"],
                
                semantic_score=analysis_result["semantic_score"],
                skill_score=analysis_result["skill_score"],
                experience_score=analysis_result["experience_score"],
                education_score=analysis_result["education_score"],
                
                matched_skills=analysis_result["matched_skills"],
                missing_skills=analysis_result["missing_skills"],
                recommendations=analysis_result["recommendations"]
            )
        except Exception as e:
            return Response(
                {"error": f"Gagal menyimpan hasil: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 7. Format dan return response
        response_data = AnalysisService.format_api_response(job_match)
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {"error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_match_detail(request, match_id):
    """
    GET /api/analysis/match/<id>/
    
    Ambil detail hasil matching.
    Hanya user yang membuat match dapat mengakses.
    """
    
    try:
        # Cek apakah match dengan ID tersebut ada
        try:
            match = JobMatch.objects.get(id=match_id)
        except JobMatch.DoesNotExist:
            return Response(
                {"error": "Match tidak ditemukan"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cek apakah user memiliki akses ke match ini
        if match.user != request.user:
            return Response(
                {"error": "Anda tidak memiliki akses ke match ini"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_data = AnalysisService.format_api_response(match)
        return Response(response_data, status=status.HTTP_200_OK)
    
    except JobMatch.DoesNotExist:
        return Response(
            {"error": "Match tidak ditemukan"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_matches(request):
    """
    GET /api/analysis/matches/
    
    List semua matches milik user yang authenticated.
    """
    
    try:
        matches = JobMatch.objects.filter(user=request.user).order_by('-created_at')
        
        response_data = [
            AnalysisService.format_api_response(match)
            for match in matches
        ]
        
        return Response({
            "count": len(response_data),
            "results": response_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
