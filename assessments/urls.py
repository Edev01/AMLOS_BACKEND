from django.urls import path
from .views import (
    CreateAssessmentModelView,
    AvailableAssessmentsView,
    AssessmentDetailView,
    SubmitAssessmentView,
    AssessmentMetadataView,
    ListAllAssessmentModelsView,
    UpdateAssessmentModelView,
    DeleteAssessmentModelView,
    SubmitHandwrittenAssessmentView,
    ListStudentSubmissionsView,
    GradeStudentAssessmentView,
    CreateExamTypeView,
    ListExamTypesView,
    UpdateExamTypeView,
    DeleteExamTypeView,
    BulkUploadQuestionsView
)

urlpatterns = [
    path('models', CreateAssessmentModelView.as_view(), name='create-assessment-model'),
    path('models/all', ListAllAssessmentModelsView.as_view(), name='list-assessment-models'),
    path('available', AvailableAssessmentsView.as_view(), name='available-assessments'),
    path('models/<int:id>', AssessmentDetailView.as_view(), name='assessment-detail'),
    path('models/<int:id>/submit', SubmitAssessmentView.as_view(), name='submit-assessment'),
    path('models/<int:id>/submit-handwritten', SubmitHandwrittenAssessmentView.as_view(), name='submit-handwritten-assessment'),
    path('models/<int:id>/update', UpdateAssessmentModelView.as_view(), name='update-assessment-model'),
    path('models/<int:id>/delete', DeleteAssessmentModelView.as_view(), name='delete-assessment-model'),
    path('metadata', AssessmentMetadataView.as_view(), name='assessment-metadata'),
    path('submissions', ListStudentSubmissionsView.as_view(), name='list-student-submissions'),
    path('submissions/<int:submission_id>/grade', GradeStudentAssessmentView.as_view(), name='grade-student-assessment'),
    path('exam-types', CreateExamTypeView.as_view(), name='create-exam-type'),
    path('exam-types/list', ListExamTypesView.as_view(), name='list-exam-types'),
    path('exam-types/<int:id>/update', UpdateExamTypeView.as_view(), name='update-exam-type'),
    path('exam-types/<int:id>/delete', DeleteExamTypeView.as_view(), name='delete-exam-type'),
    path('bulk-upload', BulkUploadQuestionsView.as_view(), name='bulk-upload-questions'),
]

