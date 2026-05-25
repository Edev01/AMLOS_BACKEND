from unicodedata import name
from django.urls import path
from .views import (
    CreateStudyPlanView, 
    ListStudyPlansView, 
    StudyPlanDetailView,
    StudyPlanDayView,
    MarkSLOCompleteView,
    CompleteStudyPlanView,
    GetActivePlanView,
    RecommendedPlansView,
    GetPlanHistory,
    SelectRecommendedPlanView,
    UpdateStudyPlanView,
    DeleteStudyPlanView,
    UpdateTimeSpentView,
    GetTimeSpentHistoryView,
    GetLeaderboardView,
    SchoolStudentCustomPlansView
)

urlpatterns = [
    # USAGE: Create a Dynamic Custom Plan (Student) or a Recommended Plan (Admin)
    # ROLE: STUDENT, ADMIN
    path('create', CreateStudyPlanView.as_view(), name='create-study-plan'),

    # USAGE: View and Manage all plans in the system
    # ROLE: ADMIN ONLY
    path('', ListStudyPlansView.as_view(), name='list-study-plans'),

    # USAGE: Student Dashboard API - Automatically finds and syncs/recalculates the current active plan
    # ROLE: STUDENT, ADMIN
    path('current', GetActivePlanView.as_view(), name='current-study-plan'),

    # USAGE: Fetch available Recommended plans for a student's grade (before they start one)
    # ROLE: STUDENT
    path('recommended', RecommendedPlansView.as_view(), name='recommended-study-plans'),

    # USAGE: View full details of a specific plan by ID
    # ROLE: STUDENT (Owner), ADMIN
    path('<int:plan_id>', StudyPlanDetailView.as_view(), name='study-plan-detail'),

    # USAGE: Update and recalculate a specific plan
    # ROLE: STUDENT (Owner), ADMIN
    path('<int:plan_id>/update', UpdateStudyPlanView.as_view(), name='update-study-plan'),
    
    # USAGE: Delete a recommended plan
    # ROLE: ADMIN ONLY
    path('<int:plan_id>/delete', DeleteStudyPlanView.as_view(), name='delete-study-plan'),

    # USAGE: Fetch a specific day's scheduled SLOs for a plan
    # ROLE: STUDENT, ADMIN
    path('<int:plan_id>/day/<str:date>', StudyPlanDayView.as_view(), name='study-plan-day'),

    # USAGE: Manually finish an active  plan early so a new one can be created.
    # ROLE: STUDENT, ADMIN
    path('<int:plan_id>/complete', CompleteStudyPlanView.as_view(), name='complete-study-plan'),

    # USAGE: Mark a specific SLO as finished for progress tracking
    # ROLE: STUDENT ONLY
    path('slo/<int:plan_slo_id>/complete', MarkSLOCompleteView.as_view(), name='mark-slo-complete'),
    

    path('history', GetPlanHistory.as_view(), name = 'plan-history'),
    
    # USAGE: Select a recommended plan to make it the student's active plan
    # ROLE: STUDENT
    path('recommended/<int:plan_id>/select', SelectRecommendedPlanView.as_view(), name='select-recommended-plan'),
    
    # Daily Study Time-spent APIs
    path('time-spent/update', UpdateTimeSpentView.as_view(), name='update-time-spent'),
    path('time-spent/history', GetTimeSpentHistoryView.as_view(), name='time-spent-history'),
    path('time-spent/leaderboard', GetLeaderboardView.as_view(), name='time-spent-leaderboard'),
    
    # USAGE: Fetch all custom plans for a specific student
    # ROLE: SCHOOL
    path('school/student/<int:student_id>/plans', SchoolStudentCustomPlansView.as_view(), name='school-student-plans'),
]
