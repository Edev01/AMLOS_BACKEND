from django.urls import path
from .views import (
    CreateAssessmentModelView,
    AvailableAssessmentsView,
    AssessmentDetailView,
    SubmitAssessmentView,
    AssessmentMetadataView
)

urlpatterns = [
    path('models', CreateAssessmentModelView.as_view(), name='create-assessment-model'),
    path('available', AvailableAssessmentsView.as_view(), name='available-assessments'),
    path('models/<int:id>', AssessmentDetailView.as_view(), name='assessment-detail'),
    path('models/<int:id>/submit', SubmitAssessmentView.as_view(), name='submit-assessment'),
    path('metadata', AssessmentMetadataView.as_view(), name='assessment-metadata'),
]
