
from django.urls import path

from .views import ResumeUploadView, ResumeListView

urlpatterns = [
    path(
        "upload/",
        ResumeUploadView.as_view(),
        name="resume-upload"
    ),
    path(
        "list/",
        ResumeListView.as_view(),
        name="resume-list"
    ),
]
