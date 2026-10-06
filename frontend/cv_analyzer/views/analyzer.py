import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..forms import CVUploadForm, JobDescriptionForm
from ..ml_services import analyze_cv, recommend_career
from ..models import AnalysisLog

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def cv_analyzer(request):
    if request.method == 'POST':
        cv_form = CVUploadForm(request.POST, request.FILES)
        job_form = JobDescriptionForm(request.POST)
        if cv_form.is_valid() and job_form.is_valid():
            try:
                cv_file = request.FILES['cv_file']
                job_description = job_form.cleaned_data['job_description']
                mode = request.POST.get('mode', 'match')

                # Save file temporarily
                fs = FileSystemStorage()
                filename = fs.save(cv_file.name, cv_file)
                file_path = fs.path(filename)

                # Process based on mode
                if mode == 'match':
                    results = analyze_cv(file_path, job_description)
                else:
                    results = recommend_career(file_path)

                # Save to database
                analysis = AnalysisLog.objects.create(
                    user=request.user,
                    cv_file=cv_file.name,
                    job_description=job_description,
                    results=results,
                    mode=mode,
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

                return redirect('analyzer:analysis_results', analysis_id=analysis.id)
            except Exception as e:
                logger.error(f"Analysis failed: {str(e)}")
                messages.error(request, f"Analysis failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        cv_form = CVUploadForm()
        job_form = JobDescriptionForm()

    return render(request, 'analyzer/form.html', {
        'cv_form': cv_form,
        'job_form': job_form,
        'enable_pixel_bg': True,
    })


@login_required
@require_http_methods(["GET"])
def analysis_results(request, analysis_id):
    try:
        analysis = AnalysisLog.objects.get(id=analysis_id, user=request.user)
        return render(request, 'analyzer/result.html', {'analysis': analysis})
    except AnalysisLog.DoesNotExist:
        messages.error(request, "Analysis not found or you don't have permission to view it.")
        return redirect('analyzer:dashboard')
