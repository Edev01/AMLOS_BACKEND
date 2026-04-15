from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from utils.response_builder import response_builder
from accounts.permissions import IsRole
from .models import StudyPlan, StudyPlanSLO
from .serializers import (
    CreateStudyPlanSerializer, 
    StudyPlanSerializer, 
    StudyPlanDetailSerializer, 
    ValidatePlanSerializer,
    StudyPlanSLOSerializer
)
from .engine import StudyPlanEngine
from django.db import models

class CreateStudyPlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'STUDENT']

    def post(self, request):
        user = request.user
        data = request.data
        serializer = CreateStudyPlanSerializer(data=data)
        if serializer.is_valid():
            if user.role == 'STUDENT':
                data['grade'] = user.get_profile().grade
            elif user.role == 'ADMIN':
                data['grade'] = data.get('grade')
                if not data['grade']:
                    return response_builder(
                        success=False,
                        message="Grade is required for ADMIN.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            # Check if user already has an active plan
            if StudyPlan.objects.filter(user=user, status=StudyPlan.Status.ACTIVE).exists():
                return response_builder(
                    success=False,
                    message="You already have an active study plan. Please finish it before creating a new one.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            plan_type = serializer.validated_data.get('plan_type')
            if plan_type == StudyPlan.PlanType.RECOMMENDED and request.user.role != 'ADMIN':
                return response_builder(
                    success=False,
                    message="Only Admins can create recommended plans.",
                    status_code=status.HTTP_403_FORBIDDEN
                )

            plan = serializer.save(user=request.user)
            
            engine = StudyPlanEngine(serializer.validated_data)
            try:
                count = engine.generate_schedule(plan)
                return response_builder(
                    success=True,
                    message=f"Study plan created with {count} scheduled SLOs.",
                    data=StudyPlanSerializer(plan).data,
                    status_code=status.HTTP_201_CREATED
                )
            except Exception as e:
                plan.delete()
                return response_builder(
                    success=False,
                    message=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class CompleteStudyPlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT', 'ADMIN']

    def post(self, request, plan_id):
        # Users can complete their own plans; Admin can complete any.
        if request.user.role == 'ADMIN':
            plan = get_object_or_404(StudyPlan, id=plan_id)
        else:
            plan = get_object_or_404(StudyPlan, id=plan_id, user=request.user)
            
        plan.status = StudyPlan.Status.COMPLETED
        plan.save()
        
        return response_builder(
            success=True,
            message="Study plan marked as completed. You can now create a new one.",
            data={"id": plan.id, "status": plan.status}
        )

class ListStudyPlansView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN'] # Admin only now

    def get(self, request):
        # Admins see all plans created by them or all recommended plans
        plans = StudyPlan.objects.all()
        serializer = StudyPlanSerializer(plans, many=True)
        return response_builder(success=True, message="All plans fetched (Admin).", data=serializer.data)

class RecommendedPlansView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def get(self, request):
        # Students see Recommended plans matching their grade
        profile = request.user.get_get_profile() if hasattr(request.user, 'get_get_profile') else None
        grade = profile.grade if profile and hasattr(profile, 'grade') else ""
        
        plans = StudyPlan.objects.filter(
            plan_type=StudyPlan.PlanType.RECOMMENDED, 
            grade=grade
        )
        
        serializer = StudyPlanSerializer(plans, many=True)
        return response_builder(success=True, message="Recommended plans fetched.", data=serializer.data)

class GetActivePlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT', 'ADMIN']

    def get(self, request):
        # Find the active plan for the user
        plan = StudyPlan.objects.filter(user=request.user, status=StudyPlan.Status.ACTIVE).first()
        
        if not plan:
            return response_builder(
                success=False,
                message="No active study plan found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Trigger Auto-Sync Recalculation (24h check)
        plan_data = {
            'slo_ids': list(plan.scheduled_slos.values_list('slo_id', flat=True)),
            'mode': plan.mode,
            'start_date': plan.start_date,
            'end_date': plan.end_date,
            'min_study_time_daily': plan.min_study_time_daily,
            'max_study_time_daily': plan.max_study_time_daily,
            'subject_order': plan.subject_order,
            'custom_pattern': plan.custom_pattern,
        }
        engine = StudyPlanEngine(plan_data)
        recalculated = engine.recalculate_if_needed(plan)
        
        if recalculated:
             plan.refresh_from_db()

        serializer = StudyPlanDetailSerializer(plan)
        return response_builder(
            success=True,
            message="Active plan fetched." + (" (Recalculated)" if recalculated else ""),
            data=serializer.data
        )

class StudyPlanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'STUDENT']

    def get(self, request, plan_id):
        plan = get_object_or_404(StudyPlan, id=plan_id)
        if request.user.role != 'ADMIN' and plan.user != request.user:
             if plan.plan_type != StudyPlan.PlanType.RECOMMENDED:
                 return response_builder(success=False, message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
        
        # Trigger Auto-Sync Recalculation (24h check)
        # We wrap plan in a dict for the engine init
        plan_data = {
            'slo_ids': list(plan.scheduled_slos.values_list('slo_id', flat=True)),
            'mode': plan.mode,
            'start_date': plan.start_date,
            'end_date': plan.end_date,
            'min_study_time_daily': plan.min_study_time_daily,
            'max_study_time_daily': plan.max_study_time_daily,
            'subject_order': plan.subject_order,
            'custom_pattern': plan.custom_pattern,
        }
        engine = StudyPlanEngine(plan_data)
        recalculated = engine.recalculate_if_needed(plan)
        
        if recalculated:
             plan.refresh_from_db() # Get updated is_completable, etc.

        serializer = StudyPlanDetailSerializer(plan)
        return response_builder(
            success=True,
            message="Plan details fetched." + (" (Recalculated due to 24h sync)" if recalculated else ""),
            data=serializer.data
        )

class MarkSLOCompleteView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def post(self, request, plan_slo_id):
        # Only students can mark their own SLOs as complete
        plan_slo = get_object_or_404(StudyPlanSLO, id=plan_slo_id, plan__user=request.user)
        plan_slo.is_completed = True
        plan_slo.save()
        
        return response_builder(
            success=True,
            message="SLO marked as completed.",
            data={"id": plan_slo.id, "is_completed": True}
        )

class StudyPlanDayView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'STUDENT']

    def get(self, request, plan_id, date):
        slos = StudyPlanSLO.objects.filter(plan_id=plan_id, scheduled_date=date)
        serializer = StudyPlanSLOSerializer(slos, many=True)
        return response_builder(
            success=True,
            message=f"SLOs for {date} fetched.",
            data=serializer.data
        )
