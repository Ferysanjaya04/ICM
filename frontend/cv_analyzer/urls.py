from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.home, name='home'),
    path('playground/', views.cv_analyzer, name='playground'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    path('help/', views.help_page, name='help'),
    path('privacy/', views.privacy, name='privacy'),
    path('accounts/login/', views.user_login, name='login'),
    path('accounts/register/', views.user_register, name='register'),
    path('accounts/logout/', views.user_logout, name='logout'),
    path('api/match-cv/', views.api_match_cv, name='api_match_cv'),
    path('api/recommend-career/', views.api_recommend_career, name='api_recommend_career'),
    path('analysis/<uuid:analysis_id>/', views.analysis_results, name='analysis_results'),
]