import logging

from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..ml_services import analyze_cv, recommend_career
from ..models import AnalysisLog

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def api_match_cv(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        cv_file = request.FILES.get('cv_file')
        job_description = request.POST.get('job_description', '')

        if not cv_file or not job_description:
            return JsonResponse({'error': 'CV file and job description are required'}, status=400)

        # Save temporarily
        fs = FileSystemStorage()
        filename = fs.save(cv_file.name, cv_file)
        file_path = fs.path(filename)

        # Process
        results = analyze_cv(file_path, job_description)

        # Save to database
        analysis = AnalysisLog.objects.create(
            user=request.user,
            cv_file=cv_file.name,
            job_description=job_description,
            results=results,
            mode='match',
            compatibility_score=results.get('compatibility_score', 0),
            compatibility_level=results.get('compatibility_level', 'LOW'),
            top_roles=results.get('top_roles', []),
            skill_gap_matched=results.get('skill_gap_matched', []),
            skill_gap_missing=results.get('skill_gap_missing', []),
            roadmap=results.get('roadmap', []),
            processing_time_ms=results.get('processing_time_ms', 0)
        )

        # Clean up
        fs.delete(filename)

        return JsonResponse({
            'status': 'success',
            'analysis_id': analysis.id,
            'results': results
        })
    except Exception as e:
        logger.error(f"API analysis failed: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_recommend_career(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    try:
        cv_file = request.FILES.get('cv_file')

        if not cv_file:
            return JsonResponse({'error': 'CV file is required'}, status=400)

        # Save temporarily
        fs = FileSystemStorage()
        filename = fs.save(cv_file.name, cv_file)
        file_path = fs.path(filename)

        # Process
        results = recommend_career(file_path)

        # Save to database
        analysis = AnalysisLog.objects.create(
            user=request.user,
            cv_file=cv_file.name,
            job_description='',
            results=results,
            mode='career',
            compatibility_score=results.get('compatibility_score', 0),
            compatibility_level=results.get('compatibility_level', 'LOW'),
            top_roles=results.get('top_roles', []),
            skill_gap_matched=results.get('skill_gap_matched', []),
            skill_gap_missing=results.get('skill_gap_missing', []),
            roadmap=results.get('roadmap', []),
            processing_time_ms=results.get('processing_time_ms', 0)
        )

        # Clean up
        fs.delete(filename)

        return JsonResponse({
            'status': 'success',
            'analysis_id': analysis.id,
            'results': results
        })
    except Exception as e:
        logger.error(f"API recommendation failed: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
