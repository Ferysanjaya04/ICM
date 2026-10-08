from django.urls import path
from .api.client import APIClient

api_client = APIClient()

urlpatterns = [
    path("analyze/", lambda request: api_client.analyze_cv(request.FILES["cv"], request.POST["job_description"])),
    path("recommend/", lambda request: api_client.get_recommendation(request.FILES["cv"])),
    path("auth/login/", lambda request: api_client.login(request.POST["username"], request.POST["password"])),
    path("auth/register/", lambda request: api_client.register(request.POST["username"], request.POST["email"], request.POST["password"])),
    path("dashboard/", lambda request: {"message": "Dashboard view"}),
    path("about/", lambda request: {"message": "About page"}),
    path("help/", lambda request: {"message": "Help page"}),
    path("privacy/", lambda request: {"message": "Privacy policy"}),
]