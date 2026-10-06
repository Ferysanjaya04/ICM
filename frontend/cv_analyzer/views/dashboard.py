from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from ..models import AnalysisLog


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    base_qs = AnalysisLog.objects.filter(user=request.user).order_by('-created_at')
    analyses = list(base_qs[:10])
    total = base_qs.count()
    avg = base_qs.aggregate(models.Avg('compatibility_score'))['compatibility_score__avg'] or 0
    first = base_qs.first()
    top_role = 'N/A'
    if first and first.top_roles:
        try:
            top_role = first.top_roles[0].get('role', 'N/A')
        except (AttributeError, IndexError, TypeError):
            top_role = 'N/A'
    stats = {
        'total_analyses': total,
        'average_score': avg,
        'top_role': top_role,
        'improvement_rate': 0  # Placeholder for future implementation
    }
    return render(request, 'dashboard/index.html', {
        'analyses': analyses,
        'stats': stats
    })
