from django.urls import path
from .views import CreateSubjectView, CreateChapterView, CreateSLOView

urlpatterns = [
    path('subjects/create', CreateSubjectView.as_view()),
    path('chapters/create', CreateChapterView.as_view()),
    path('slos/create', CreateSLOView.as_view()),
]
