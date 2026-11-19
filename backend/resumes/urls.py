
from django.urls import path

from .views import ResumeUploadView, ResumeListView, ResumeDownloadView

urlpatterns = [
    path(
        "<uuid:resume_id>/download/",
        ResumeDownloadView.as_view(),
        name="resume-download",
    ),
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
