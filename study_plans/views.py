import logging
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from utils.response_builder import response_builder
from accounts.permissions import IsRole
from .models import StudyPlan, StudyPlanSLO, DailyTimeSpent
from curriculum.models import SLO
from .serializers import (
    CreateStudyPlanSerializer, 
    StudyPlanSerializer, 
    StudyPlanDetailSerializer, 
    ValidatePlanSerializer,
    StudyPlanHistorySerializer,
    StudyPlanSLOSerializer
)
from .engine import StudyPlanEngine
from django.db import models
from django.db.models import Prefetch
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class CreateStudyPlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'STUDENT']

    def post(self, request):
        user = request.user
        data = request.data
        serializer = CreateStudyPlanSerializer(data=data)
        if serializer.is_valid():
            # grade check logic changed, but i'm letting it same for both, free will :)
            if user.role == 'STUDENT':
                data['grade'] = data.get('grade')
            elif user.role == 'ADMIN':
                data['grade'] = data.get('grade')
                if not data['grade']:
                    return response_builder(
                        success=False,
                        message="Grade is required for ADMIN.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            # Check if user already has an active plan
            if user.role == 'STUDENT':
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
        # Admins see only recommended plans
        plans = StudyPlan.objects.filter(plan_type=StudyPlan.PlanType.RECOMMENDED).prefetch_related(
            Prefetch(
                'scheduled_slos',
                queryset=StudyPlanSLO.objects.select_related('slo')
            )
        )
        serializer = StudyPlanDetailSerializer(plans, many=True)
        return response_builder(success=True, message="Recommended plans fetched (Admin).", data=serializer.data)

class RecommendedPlansView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def get(self, request):
        # Students see Recommended plans matching their grade
        profile = request.user.get_profile() if hasattr(request.user, 'get_profile') else None
        print("request.user.get_get_profile():", request.user.get_profile())
        grade = profile.grade if profile and hasattr(profile, 'grade') else ""
        print("grade:", grade)
        
        plans = StudyPlan.objects.filter(
            plan_type=StudyPlan.PlanType.RECOMMENDED, 
            grade=grade
        ).prefetch_related(
            Prefetch(
                'scheduled_slos',
                queryset=StudyPlanSLO.objects.select_related('slo')
            )
        )
        
        serializer = StudyPlanDetailSerializer(plans, many=True)
        return response_builder(success=True, message="Recommended plans fetched with full details.", data=serializer.data)

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
        
        # Streak break check
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        if plan.last_streak_date and plan.last_streak_date < yesterday:
            plan.current_streak = 0
            plan.save()

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

        # Streak break check
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        if plan.last_streak_date and plan.last_streak_date < yesterday:
            plan.current_streak = 0
            plan.save()

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
        plan_slo.completed_at = timezone.now()
        plan_slo.save()
        
        # Streak logic
        plan = plan_slo.plan
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        if plan.last_streak_date == yesterday:
            plan.current_streak += 1
            plan.last_streak_date = today
        elif plan.last_streak_date == today:
            # Already completed something today, streak stays the same
            pass
        else:
            # Streak broken or first time
            plan.current_streak = 1
            plan.last_streak_date = today
            
        plan.save()
        
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
class GetPlanHistory(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def get(self, request):
        user = request.user

        plans = StudyPlan.objects.filter(user=user)\
            .exclude(status=StudyPlan.Status.ACTIVE)\
            .prefetch_related(
                Prefetch(
                    'scheduled_slos',
                    queryset=StudyPlanSLO.objects.select_related('slo')
                )
            )\
            .order_by('-created_at')

        serializer = StudyPlanHistorySerializer(plans, many=True)

        return response_builder(
            success=True,
            message="Study plan history fetched with SLOs.",
            data=serializer.data
        )

class UpdateStudyPlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT', 'ADMIN']

    def post(self, request, plan_id):
        user = request.user
        logger.info(f"UpdateStudyPlanView: Received update request for plan_id={plan_id} from user={user.email}")
        
        plan = get_object_or_404(StudyPlan, id=plan_id)
        
        # Role-based restriction: Admins edit RECOMMENDED, Students edit CUSTOM (their own)
        if user.role == 'ADMIN':
            if plan.plan_type != StudyPlan.PlanType.RECOMMENDED:
                logger.warning(f"UpdateStudyPlanView: Admin attempted to edit non-recommended plan_id={plan_id}")
                return response_builder(success=False, message="Admins can only edit recommended plans.", status_code=status.HTTP_400_BAD_REQUEST)
        elif user.role == 'STUDENT':
            if plan.user != user:
                logger.warning(f"UpdateStudyPlanView: Access denied for user={user.email} on plan_id={plan_id}")
                return response_builder(success=False, message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
            if plan.plan_type != StudyPlan.PlanType.CUSTOM:
                logger.warning(f"UpdateStudyPlanView: Attempt to edit non-custom plan_id={plan_id}")
                return response_builder(success=False, message="Students can only edit custom plans.", status_code=status.HTTP_400_BAD_REQUEST)

        serializer = CreateStudyPlanSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            logger.info(f"UpdateStudyPlanView: Serializer is valid for plan_id={plan_id}")
            # Save metadata updates
            plan = serializer.save()
            
            new_slo_ids = serializer.validated_data.get('slo_ids', [])
            logger.debug(f"UpdateStudyPlanView: New SLO IDs: {new_slo_ids}")
            
            # Recalculation logic:
            # 1. Identify currently completed SLOs
            completed_slos_query = StudyPlanSLO.objects.filter(plan=plan, is_completed=True)
            completed_slo_ids = list(completed_slos_query.values_list('slo_id', flat=True))
            logger.debug(f"UpdateStudyPlanView: Completed SLO IDs: {completed_slo_ids}")
            
            # 2. Handle removals: If a completed SLO is no longer in new_slo_ids, delete it
            to_delete_completed = completed_slos_query.exclude(slo_id__in=new_slo_ids)
            delete_count = to_delete_completed.count()
            if delete_count > 0:
                logger.info(f"UpdateStudyPlanView: Deleting {delete_count} previously completed SLOs that are no longer in the plan.")
                to_delete_completed.delete()
            
            # 3. Determine which SLOs to schedule (those in new_slo_ids but not already completed)
            to_schedule_ids = [sid for sid in new_slo_ids if sid not in completed_slo_ids]
            logger.info(f"UpdateStudyPlanView: SLOs to schedule: {len(to_schedule_ids)}")
            
            # 4. Clear all incomplete SLOs
            incomplete_count = StudyPlanSLO.objects.filter(plan=plan, is_completed=False).count()
            logger.info(f"UpdateStudyPlanView: Clearing {incomplete_count} incomplete SLOs.")
            StudyPlanSLO.objects.filter(plan=plan, is_completed=False).delete()
            
            # 5. Fetch SLO models for scheduling
            to_schedule_slos = list(SLO.objects.filter(id__in=to_schedule_ids).select_related('chapter', 'chapter__subject'))
            
            # 6. Re-run distribution
            today = timezone.now().date()
            # If plan hasn't started yet, schedule from start_date
            # Otherwise, schedule from today
            calc_start_date = max(plan.start_date, today)
            logger.info(f"UpdateStudyPlanView: Recalculating from date={calc_start_date}")
            
            engine = StudyPlanEngine(serializer.validated_data)
            try:
                count = engine.generate_schedule(plan, slos=to_schedule_slos, start_date=calc_start_date)
                
                # Update last_recalculated_at
                plan.last_recalculated_at = today
                plan.save()
                
                logger.info(f"UpdateStudyPlanView: Successfully updated plan_id={plan_id}. {count} SLOs scheduled.")
                return response_builder(
                    success=True,
                    message=f"Study plan updated and recalculated. {count} SLOs scheduled.",
                    data=StudyPlanSerializer(plan).data,
                    status_code=status.HTTP_200_OK
                )
            except Exception as e:
                logger.exception(f"UpdateStudyPlanView: Recalculation failed for plan_id={plan_id}")
                return response_builder(
                    success=False,
                    message=f"Recalculation failed: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        logger.error(f"UpdateStudyPlanView: Validation failed for plan_id={plan_id}. Errors: {serializer.errors}")
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class DeleteStudyPlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def delete(self, request, plan_id):
        user = request.user
        logger.info(f"DeleteStudyPlanView: Received delete request for plan_id={plan_id} from user={user.email}")
        
        plan = get_object_or_404(StudyPlan, id=plan_id)
        
        # Only recommended plans can be deleted by admin here
        if plan.plan_type != StudyPlan.PlanType.RECOMMENDED:
            logger.warning(f"DeleteStudyPlanView: Admin attempted to delete non-recommended plan_id={plan_id}")
            return response_builder(
                success=False, 
                message="Admins can only delete recommended plans.", 
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        plan_title = plan.title
        plan.delete()
        
        logger.info(f"DeleteStudyPlanView: Successfully deleted recommended plan_id={plan_id} ({plan_title})")
        return response_builder(
            success=True,
            message=f"Recommended plan '{plan_title}' has been deleted.",
            status_code=status.HTTP_200_OK
        )

class SelectRecommendedPlanView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def post(self, request, plan_id):
        user = request.user
        
        # Check if student already has an active plan
        if StudyPlan.objects.filter(user=user, status=StudyPlan.Status.ACTIVE).exists():
            return response_builder(
                success=False,
                message="You already have an active study plan. Please finish it before selecting a new one.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get the recommended plan template
        template_plan = get_object_or_404(StudyPlan, id=plan_id, plan_type=StudyPlan.PlanType.RECOMMENDED)

        # Clone the plan for the student
        # Note: We set plan_type to CUSTOM or RECOMMENDED depending on how you want to track it.
        # Keeping it as RECOMMENDED but owned by the student helps distinguish it.
        new_plan = StudyPlan.objects.create(
            user=user,
            plan_type=StudyPlan.PlanType.RECOMMENDED, 
            grade=template_plan.grade,
            title=f"{template_plan.title} (Selected)",
            mode=template_plan.mode,
            start_date=template_plan.start_date,
            end_date=template_plan.end_date,
            min_study_time_daily=template_plan.min_study_time_daily,
            max_study_time_daily=template_plan.max_study_time_daily,
            custom_pattern=template_plan.custom_pattern,
            subject_order=template_plan.subject_order,
            total_slo_time=template_plan.total_slo_time,
            total_available_time=template_plan.total_available_time,
            status=StudyPlan.Status.ACTIVE,
            last_recalculated_at=timezone.now().date()
        )

        # Clone the scheduled SLOs (the actual schedule/timeline)
        template_slos = template_plan.scheduled_slos.all()
        new_slos = []
        for t_slo in template_slos:
            new_slos.append(StudyPlanSLO(
                plan=new_plan,
                slo=t_slo.slo,
                scheduled_date=t_slo.scheduled_date,
                order_in_day=t_slo.order_in_day,
                subject_name=t_slo.subject_name,
                chapter_name=t_slo.chapter_name,
                estimated_time=t_slo.estimated_time,
                is_completed=False
            ))
        
        if new_slos:
            StudyPlanSLO.objects.bulk_create(new_slos)

        # Return the same schema as a custom plan using DetailSerializer
        serializer = StudyPlanDetailSerializer(new_plan)
        return response_builder(
            success=True,
            message="Recommended plan has been activated for you.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class UpdateTimeSpentView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def post(self, request):
        seconds = request.data.get('seconds', 0)
        try:
            seconds = int(seconds)
        except (ValueError, TypeError):
            return response_builder(
                success=False,
                message="Invalid 'seconds' parameter.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        today = timezone.now().date()
        daily_record, created = DailyTimeSpent.objects.get_or_create(
            user=request.user,
            date=today,
            defaults={'time_spent_seconds': 0}
        )
        daily_record.time_spent_seconds += seconds
        daily_record.save()

        return response_builder(
            success=True,
            message="Time spent updated successfully.",
            data={
                "date": str(today),
                "total_time_spent_seconds": daily_record.time_spent_seconds
            },
            status_code=status.HTTP_200_OK
        )

class GetTimeSpentHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        # We will return the history for the last 7 days
        history_data = []
        for i in range(6, -1, -1):
            day_date = today - timedelta(days=i)
            
            # Get time spent for this day
            daily_record = DailyTimeSpent.objects.filter(user=user, date=day_date).first()
            time_spent = daily_record.time_spent_seconds if daily_record else 0
            
            # Count SLOs completed on this day
            completed_slos_count = StudyPlanSLO.objects.filter(
                plan__user=user,
                is_completed=True,
                completed_at__date=day_date
            ).count()
            
            history_data.append({
                "date": str(day_date),
                "day_name": day_date.strftime("%a"), # e.g. Mon, Tue
                "time_spent_seconds": time_spent,
                "completed_slos_count": completed_slos_count
            })
            
        return response_builder(
            success=True,
            message="Daily study history and efficiency fetched.",
            data=history_data,
            status_code=status.HTTP_200_OK
        )


class GetLeaderboardView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def get(self, request):
        from django.db.models import Sum
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Query total time spent for all students in the last 7 days
        weekly_standings = DailyTimeSpent.objects.values('user').annotate(
            total_seconds=Sum('time_spent_seconds')
        ).order_by('-total_seconds')

        leaderboard_data = []
        user_ids_added = set()

        rank = 1
        for standing in weekly_standings:
            user_id = standing['user']
            try:
                user_obj = User.objects.get(id=user_id)
            except User.DoesNotExist:
                continue

            total_hours = round(standing['total_seconds'] / 3600, 1)
            is_me = (user_obj == request.user)

            # Determine badge dynamically based on study persistence
            if total_hours >= 10.0:
                badge = "Productivity Beast"
            elif total_hours >= 5.0:
                badge = "Streak Master"
            else:
                badge = "Dedicated Learner"

            avatar = "female_student" if rank % 2 == 0 else "male_student"
            if is_me:
                avatar = "star"

            leaderboard_data.append({
                "rank": rank,
                "name": f"You ({user_obj.username})" if is_me else user_obj.username.capitalize(),
                "hours": f"{total_hours} hrs",
                "badge": badge,
                "isMe": is_me,
                "avatar": avatar,
                "total_seconds": standing['total_seconds']
            })
            user_ids_added.add(user_id)
            rank += 1
            if len(leaderboard_data) >= 10:
                break

        # If the requesting user has no study records registered yet, add them at the bottom
        if request.user.id not in user_ids_added:
            leaderboard_data.append({
                "rank": rank,
                "name": f"You ({request.user.username})",
                "hours": "0.0 hrs",
                "badge": "Consistency King",
                "isMe": True,
                "avatar": "star",
                "total_seconds": 0
            })



        # Sort combined results dynamically by total_seconds spent
        leaderboard_data.sort(key=lambda x: x['total_seconds'], reverse=True)

        # Normalize ranks
        for i, item in enumerate(leaderboard_data):
            item['rank'] = i + 1

        return response_builder(
            success=True,
            message="Dynamic leaderboard standings fetched successfully.",
            data=leaderboard_data[:10],
            status_code=status.HTTP_200_OK
        )