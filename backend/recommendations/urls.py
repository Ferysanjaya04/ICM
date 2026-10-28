from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CareerRecommendationViewSet, JobRoleViewSet

router = DefaultRouter()
router.register(r'recommendations', CareerRecommendationViewSet, basename='recommendation')
router.register(r'job-roles', JobRoleViewSet, basename='job-role')

urlpatterns = [
    path('', include(router.urls)),
]
