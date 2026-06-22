import random
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from collections import defaultdict

from utils.response_builder import response_builder
from accounts.permissions import IsRole
from curriculum.models import Subject, Chapter
from study_plans.models import StudyPlan, StudyPlanSLO
from .models import Question, AssessmentModel, StudentAssessment
from .serializers import QuestionSerializer, AssessmentModelSerializer, StudentAssessmentSerializer

def map_subject_name_to_question_subject(subject_name):
    mapping = {
        'Maths': 'Mathematics',
        'Mathematics': 'Mathematics'
    }
    return mapping.get(subject_name, subject_name)


class CreateAssessmentModelView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = AssessmentModelSerializer(data=request.data)
        if serializer.is_valid():
            mcq_count = serializer.validated_data.get('mcq_count', 0)
            short_count = serializer.validated_data.get('short_count', 0)
            long_count = serializer.validated_data.get('long_count', 0)
            total_questions = serializer.validated_data.get('total_questions')

            if mcq_count + short_count + long_count != total_questions:
                return response_builder(
                    success=False,
                    message="Sum of MCQ, Short, and Long question counts must equal total_questions.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            assessment = serializer.save()

            # Map chapters to "Chapter N" formats
            subject = assessment.subject
            all_subject_chapters = list(Chapter.objects.filter(subject=subject).order_by('id'))
            
            question_chapters = []
            for ch in assessment.chapters.all():
                try:
                    idx = all_subject_chapters.index(ch)
                    question_chapters.append(f"Chapter {idx + 1}")
                except ValueError:
                    pass

            q_subject = map_subject_name_to_question_subject(subject.name)

            # Query candidate questions
            questions_query = Question.objects.filter(
                subject=q_subject,
                chapter__in=question_chapters
            )

            cognitive_levels = assessment.cognitive_levels
            if cognitive_levels:
                questions_query = questions_query.filter(cognitive_level__in=cognitive_levels)

            categories = assessment.categories
            if categories:
                questions_query = questions_query.filter(category__in=categories)

            # Separate by type
            mcqs = list(questions_query.filter(question_type='MCQ'))
            shorts = list(questions_query.filter(question_type='SHORT'))
            longs = list(questions_query.filter(question_type='LONG'))

            selected = []
            if mcq_count > 0:
                selected.extend(random.sample(mcqs, min(len(mcqs), mcq_count)))
            if short_count > 0:
                selected.extend(random.sample(shorts, min(len(shorts), short_count)))
            if long_count > 0:
                selected.extend(random.sample(longs, min(len(longs), long_count)))

            assessment.questions.set(selected)

            return response_builder(
                success=True,
                message="Assessment model created successfully and questions linked.",
                data=AssessmentModelSerializer(assessment).data,
                status_code=status.HTTP_201_CREATED
            )

        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AvailableAssessmentsView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def get(self, request):
        user = request.user
        
        # Find active study plan
        active_plan = StudyPlan.objects.filter(user=user, status=StudyPlan.Status.ACTIVE).first()
        if not active_plan:
            return response_builder(
                success=False,
                message="No active study plan found.",
                data=[],
                status_code=status.HTTP_200_OK
            )

        # Get all scheduled SLOs to determine which chapters/subjects are fully completed
        scheduled_slos = list(active_plan.scheduled_slos.select_related('slo', 'slo__chapter', 'slo__chapter__subject'))
        if not scheduled_slos:
            return response_builder(
                success=True,
                message="No scheduled SLOs in the active plan.",
                data=[]
            )

        # 1. Group plan SLOs by chapter to check completion
        slos_by_chapter = defaultdict(list)
        for plan_slo in scheduled_slos:
            slos_by_chapter[plan_slo.slo.chapter].append(plan_slo)

        completed_chapters = set()
        total_chapters = set(slos_by_chapter.keys())

        for chapter, plan_slos in slos_by_chapter.items():
            if all(ps.is_completed for ps in plan_slos):
                completed_chapters.add(chapter)

        # 2. Group total chapters by subject name to compute subject-specific milestones
        chapters_by_subject = defaultdict(list)
        for chapter in total_chapters:
            chapters_by_subject[chapter.subject.name].append(chapter)

        # Get student attempts
        student_attempts = {
            sa.assessment_model_id: sa 
            for sa in StudentAssessment.objects.filter(student=user)
        }

        # 3. Fetch all assessment models for the plan's grade and subjects
        subjects_in_plan = list(chapters_by_subject.keys())
        all_potential_assessments = AssessmentModel.objects.filter(
            grade=active_plan.grade,
            subject__name__in=subjects_in_plan
        ).prefetch_related('chapters', 'subject')

        available_assessments = []

        # 4. Check unlock conditions for each assessment
        for assessment in all_potential_assessments:
            is_unlocked = False

            if assessment.assessment_type == AssessmentModel.AssessmentType.CHAPTER_WISE:
                # Chapter-wise is unlocked if all its chapters are in the student's completed_chapters
                assessment_chapters = list(assessment.chapters.all())
                if assessment_chapters and all(c in completed_chapters for c in assessment_chapters):
                    is_unlocked = True
            else:
                # Milestone assessments (Quarter, Half, etc.) are unlocked based on completion percentage per subject
                subject_name = assessment.subject.name
                sub_chapters = chapters_by_subject.get(subject_name, [])
                total_sub_chapters = len(sub_chapters)
                completed_sub_chapters = len([c for c in sub_chapters if c in completed_chapters])
                pct = (completed_sub_chapters / total_sub_chapters * 100) if total_sub_chapters > 0 else 0

                if assessment.assessment_type == AssessmentModel.AssessmentType.QUARTER and pct >= 25:
                    is_unlocked = True
                elif assessment.assessment_type == AssessmentModel.AssessmentType.HALF and pct >= 50:
                    is_unlocked = True
                elif assessment.assessment_type == AssessmentModel.AssessmentType.THIRD_QUARTER and pct >= 75:
                    is_unlocked = True
                elif assessment.assessment_type == AssessmentModel.AssessmentType.FULL_BOOK and pct == 100:
                    is_unlocked = True

            attempt = student_attempts.get(assessment.id)
            available_assessments.append({
                "id": assessment.id,
                "title": assessment.title,
                "assessment_type": assessment.assessment_type,
                "grade": assessment.grade,
                "subject_name": assessment.subject.name,
                "total_questions": assessment.total_questions,
                "is_unlocked": is_unlocked,
                "is_completed": attempt.is_completed if attempt else False,
                "score": attempt.score if attempt else 0,
                "total_marks": attempt.total_marks if attempt else 0,
                "completed_at": attempt.completed_at.isoformat() if attempt and attempt.completed_at else None
            })

        return response_builder(
            success=True,
            message="Available assessments fetched successfully.",
            data=available_assessments
        )


class AssessmentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'STUDENT']

    def get(self, request, id):
        assessment = get_object_or_404(AssessmentModel, id=id)
        questions = assessment.questions.all()
        
        # Verify access for students: they must only access unlocked assessments
        if request.user.role == 'STUDENT':
            # Check if this assessment is unlocked for this student
            active_plan = StudyPlan.objects.filter(user=request.user, status=StudyPlan.Status.ACTIVE).first()
            if not active_plan or active_plan.grade != assessment.grade:
                return response_builder(
                    success=False,
                    message="Assessment not unlocked or not belonging to your grade.",
                    status_code=status.HTTP_403_FORBIDDEN
                )

        serializer = AssessmentModelSerializer(assessment)
        questions_serializer = QuestionSerializer(questions, many=True)

        data = serializer.data
        data['questions'] = questions_serializer.data

        return response_builder(
            success=True,
            message="Assessment details and questions fetched successfully.",
            data=data
        )


class SubmitAssessmentView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['STUDENT']

    def post(self, request, id):
        assessment = get_object_or_404(AssessmentModel, id=id)
        score = request.data.get('score', 0)
        total_marks = request.data.get('total_marks', 0)

        try:
            score = int(score)
            total_marks = int(total_marks)
        except (ValueError, TypeError):
            return response_builder(
                success=False,
                message="Invalid score or total_marks format.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        attempt, created = StudentAssessment.objects.get_or_create(
            student=request.user,
            assessment_model=assessment,
            defaults={
                'score': score,
                'total_marks': total_marks,
                'is_completed': True,
                'completed_at': timezone.now()
            }
        )

        if not created:
            attempt.score = score
            attempt.total_marks = total_marks
            attempt.is_completed = True
            attempt.completed_at = timezone.now()
            attempt.save()

        return response_builder(
            success=True,
            message="Assessment results submitted successfully.",
            data=StudentAssessmentSerializer(attempt).data
        )

class AssessmentMetadataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "assessment_types": [
                {"value": choice[0], "label": choice[1]} 
                for choice in AssessmentModel.AssessmentType.choices
            ],
            "cognitive_levels": ["Knowledge", "Understanding", "Application"],
            "categories": ["Past Paper", "Book Exercise", "Additional Question", "Conceptual"],
            "question_types": ["MCQ", "SHORT", "LONG"],
            "difficulty_levels": ["Easy", "Medium", "Hard"]
        }
        return response_builder(
            success=True,
            message="Assessment enums and metadata fetched successfully.",
            data=data
        )

