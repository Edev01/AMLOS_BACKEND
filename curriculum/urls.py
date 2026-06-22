from django.urls import path
from .views import (CreateSubjectView, CreateChapterView, CreateSLOView, ListSubjectsView, ListChaptersView, BulkUploadCurriculumView,
                    CreateGradeView, ListGradesView, UpdateGradeView, DeleteGradeView,
                    UpdateSubjectView, DeleteSubjectView, UpdateChapterView, DeleteChapterView, UpdateSLOView, DeleteSLOView)

urlpatterns = [
    path('subjects/create', CreateSubjectView.as_view()),
    path('chapters/create', CreateChapterView.as_view()),
    path('slos/create', CreateSLOView.as_view()),
    path('subjects', ListSubjectsView.as_view()),
    path('chapters/<str:subject_ids>', ListChaptersView.as_view()),
    path('bulk-upload', BulkUploadCurriculumView.as_view()),
    path('grades/create', CreateGradeView.as_view()),
    path('grades', ListGradesView.as_view()),
    path('grades/<int:grade_id>/update', UpdateGradeView.as_view()),
    path('grades/<int:grade_id>/delete', DeleteGradeView.as_view()),
    path('subjects/<int:subject_id>/update', UpdateSubjectView.as_view()),
    path('subjects/<int:subject_id>/delete', DeleteSubjectView.as_view()),
    path('chapters/<int:chapter_id>/update', UpdateChapterView.as_view()),
    path('chapters/<int:chapter_id>/delete', DeleteChapterView.as_view()),
    path('slos/<int:slo_id>/update', UpdateSLOView.as_view()),
    path('slos/<int:slo_id>/delete', DeleteSLOView.as_view()),
]
