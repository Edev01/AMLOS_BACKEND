from django.urls import path
from .views import CreateSubjectView, CreateChapterView, CreateSLOView, ListSubjectsView, ListChaptersView

urlpatterns = [
    path('subjects/create', CreateSubjectView.as_view()),
    path('chapters/create', CreateChapterView.as_view()),
    path('slos/create', CreateSLOView.as_view()),
    path('subjects', ListSubjectsView.as_view()),
    path('chapters/<str:subject_ids>', ListChaptersView.as_view()),
]
