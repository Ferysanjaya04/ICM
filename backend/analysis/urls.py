"""
Analysis URLs - Routing untuk API endpoints analisis
"""

from django.urls import path
from .views import (
    analyze_cv_and_job,
    get_match_detail,
    list_user_matches
)

app_name = "analysis"

urlpatterns = [
    # POST untuk membuat analisis baru
    path("match/", analyze_cv_and_job, name="analyze"),
    
    # GET untuk list semua match user
    path("matches/", list_user_matches, name="list-matches"),
    
    # GET untuk detail satu match
    path("match/<str:match_id>/", get_match_detail, name="match-detail"),
]
