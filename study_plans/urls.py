from django.urls import path
from .views import (
    CreateStudyPlanView, 
    ListStudyPlansView, 
    StudyPlanDetailView,
    StudyPlanDayView,
    MarkSLOCompleteView,
    CompleteStudyPlanView,
    GetActivePlanView,
    RecommendedPlansView
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

    # USAGE: Fetch a specific day's scheduled SLOs for a plan
    # ROLE: STUDENT, ADMIN
    path('<int:plan_id>/day/<str:date>', StudyPlanDayView.as_view(), name='study-plan-day'),

    # USAGE: Manually finish an active  plan early so a new one can be created.
    # ROLE: STUDENT, ADMIN
    path('<int:plan_id>/complete', CompleteStudyPlanView.as_view(), name='complete-study-plan'),

    # USAGE: Mark a specific SLO as finished for progress tracking
    # ROLE: STUDENT ONLY
    path('slo/<int:plan_slo_id>/complete', MarkSLOCompleteView.as_view(), name='mark-slo-complete'),
]
