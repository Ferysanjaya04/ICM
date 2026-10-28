"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from config.views import (
    HomeView,
    LoginView,
    RegisterView,
    LogoutView,
    AnalyzerFormView,
    DashboardView,
    AnalyzerResultView,
    AboutView,
    HelpView,
    PrivacyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("analyzer/", AnalyzerFormView.as_view(), name="analyzer"),
    path("analyzer/result/<uuid:analysis_id>/", AnalyzerResultView.as_view(), name="analyzer-result"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("about/", AboutView.as_view(), name="about"),
    path("help/", HelpView.as_view(), name="help"),
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("api/auth/", include("accounts.urls")),
    path("api/resume/", include("resumes.urls")),
    path("api/analysis/", include("analysis.urls")),
    path("api/", include("recommendations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
