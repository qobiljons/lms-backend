from django.urls import path

from . import api

urlpatterns = [
    path("", api.HomeworkListCreateAPIView.as_view(), name="homework_list"),
    path("<int:homework_id>/", api.HomeworkDetailAPIView.as_view(), name="homework_detail"),
    path(
        "submissions/",
        api.HomeworkSubmissionListCreateAPIView.as_view(),
        name="homework_submission_list",
    ),
    path(
        "submissions/<int:submission_id>/",
        api.HomeworkSubmissionDetailAPIView.as_view(),
        name="homework_submission_detail",
    ),
    path(
        "submissions/<int:submission_id>/upload/",
        api.HomeworkFileUploadAPIView.as_view(),
        name="homework_file_upload",
    ),
    path(
        "submissions/<int:submission_id>/ai-grade/",
        api.AIAutoGradeAPIView.as_view(),
        name="homework_ai_grade",
    ),
]
