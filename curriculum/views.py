from rest_framework.views import APIView
from rest_framework import status
from utils.response_builder import response_builder
from .serializers import SubjectSerializer, ChapterSerializer, SLOSerializer
from accounts.permissions import IsRole
from rest_framework.permissions import IsAuthenticated
from .models import *
from django.db.models import Count
from django.shortcuts import get_object_or_404
from .serializers import GradeSerializer

class CreateSubjectView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = SubjectSerializer(data=request.data)
        if serializer.is_valid():
            subject = serializer.save()
            return response_builder(
                success=True,
                message="Subject created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class CreateChapterView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = ChapterSerializer(data=request.data)
        if serializer.is_valid():
            chapter = serializer.save()
            return response_builder(
                success=True,
                message="Chapter created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message= errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class CreateSLOView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = SLOSerializer(data=request.data)
        if serializer.is_valid():
            slo = serializer.save()
            return response_builder(
                success=True,
                message="SLO created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ListSubjectsView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'SCHOOL', 'TEACHER', 'STUDENT']       

    def get(self, request):
        subjects = Subject.objects.annotate(
            chapter_count=Count('chapters', distinct=True),
            topic_count=Count('chapters__slos', distinct=True)
        )

        # Filter out subjects that do not match the student's grade
        if request.user.role == 'STUDENT':
            student_profile = request.user.student_profile
            if student_profile:
                subjects = subjects.filter(grade=student_profile.grade)

        serializer = SubjectSerializer(subjects, many=True)
        return response_builder(
            success=True,
            message="Subjects fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class ListChaptersView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'SCHOOL', 'TEACHER', 'STUDENT']       

    def get(self, request, subject_ids):
        ids_list = [int(id_str) for id_str in subject_ids.split(',')]
        chapters = Chapter.objects.filter(subject__in=ids_list).prefetch_related('slos').annotate(
            topic_count=Count('slos', distinct=True)
        )
        serializer = ChapterSerializer(chapters, many=True)
        return response_builder(
            success=True,
            message="Chapters fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

import pandas as pd
import re
from .serializers import CurriculumBulkUploadSerializer

class BulkUploadCurriculumView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = CurriculumBulkUploadSerializer(data=request.data)
        if not serializer.is_valid():
            errors = " ".join([str(err[0]) for err in serializer.errors.values()])
            return response_builder(
                success=False,
                message=errors,
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        bulk_upload = serializer.save()
        grade = bulk_upload.grade
        file_obj = bulk_upload.uploaded_file

        try:
            df = pd.read_excel(file_obj.file)
        except Exception as e:
            return response_builder(
                success=False,
                message=f"Failed to read Excel file: {str(e)}",
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Helper to map difficulty
        def map_difficulty(level):
            level_str = str(level).strip().lower()
            if "knowledge" in level_str:
                return SLO.Difficulty.LOW
            elif "understanding" in level_str:
                return SLO.Difficulty.MEDIUM
            elif "application" in level_str:
                return SLO.Difficulty.HIGH
            return SLO.Difficulty.MEDIUM 

        created_subjects = 0
        created_chapters = 0
        created_slos = 0

        current_subject = None
        current_chapter = None

        for idx, row in df.iterrows():
            subject_name = str(row.get('Subject', '')).strip()
            if not subject_name or subject_name.lower() == 'nan':
                continue

            chapter_name = str(row.get('Chapter', '')).strip()
            topic_number = str(row.get('Topic Number', '')).strip()
            topic_description = str(row.get('Topic Description', '')).strip()
            form_of_assessment = str(row.get('Form of Assessment', '')).strip()
            cognitive_level = str(row.get('Cognitive Level', '')).strip()
            
            time_required_val = row.get('Time Required', 0)
            try:
                time_required = int(time_required_val) if pd.notna(time_required_val) else 0
            except ValueError:
                time_required = 0

            priority_val = row.get('Priority', 0)
            try:
                priority = int(priority_val) if pd.notna(priority_val) else 0
            except ValueError:
                priority = 0

            weblink = str(row.get('Weblink', '')).strip()

            if current_subject is None or current_subject.name != subject_name:
                current_subject, created = Subject.objects.get_or_create(
                    name=subject_name,
                    grade=grade,
                    defaults={'description': f"{subject_name} for Grade {grade}"}
                )
                if created:
                    created_subjects += 1

            if current_chapter is None or current_chapter.name != chapter_name:
                current_chapter, created = Chapter.objects.get_or_create(
                    subject=current_subject,
                    name=chapter_name
                )
                if created:
                    created_chapters += 1

            slo, created = SLO.objects.update_or_create(
                chapter=current_chapter,
                slo_no=topic_number,
                defaults={
                    'name': topic_description,
                    'difficulty_frequency': map_difficulty(cognitive_level),
                    'estimated_time': time_required,
                    'form_of_assessment': form_of_assessment if form_of_assessment and form_of_assessment.lower() != 'nan' else '',
                    'priority_score': priority,
                    'google_drive_link': weblink if weblink and weblink.lower() != 'nan' else ''
                }
            )
            if created:
                created_slos += 1

        return response_builder(
            success=True,
            message=f"Bulk upload successful! Created {created_subjects} subjects, {created_chapters} chapters, and {created_slos} SLOs.",
            data={'upload_id': bulk_upload.id},
            status_code=status.HTTP_201_CREATED
        )

class CreateGradeView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = GradeSerializer(data=request.data)
        if serializer.is_valid():
            grade = serializer.save()
            return response_builder(
                success=True,
                message="Grade created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(success=False, message=errors, data=None, status_code=status.HTTP_400_BAD_REQUEST)

class ListGradesView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'SCHOOL', 'TEACHER', 'STUDENT']

    def get(self, request):
        grades = Grade.objects.all()
        serializer = GradeSerializer(grades, many=True)
        return response_builder(
            success=True,
            message="Grades fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class UpdateGradeView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def patch(self, request, grade_id):
        grade = get_object_or_404(Grade, id=grade_id)
        serializer = GradeSerializer(grade, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return response_builder(
                success=True,
                message="Grade updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(success=False, message=errors, data=None, status_code=status.HTTP_400_BAD_REQUEST)

class DeleteGradeView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def delete(self, request, grade_id):
        grade = get_object_or_404(Grade, id=grade_id)
        grade.delete()
        return response_builder(
            success=True,
            message="Grade deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )

class UpdateSubjectView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def patch(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        serializer = SubjectSerializer(subject, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return response_builder(
                success=True,
                message="Subject updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(success=False, message=errors, data=None, status_code=status.HTTP_400_BAD_REQUEST)

class DeleteSubjectView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def delete(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        subject.delete()
        return response_builder(
            success=True,
            message="Subject deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )

class UpdateChapterView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def patch(self, request, chapter_id):
        chapter = get_object_or_404(Chapter, id=chapter_id)
        serializer = ChapterSerializer(chapter, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return response_builder(
                success=True,
                message="Chapter updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(success=False, message=errors, data=None, status_code=status.HTTP_400_BAD_REQUEST)

class DeleteChapterView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def delete(self, request, chapter_id):
        chapter = get_object_or_404(Chapter, id=chapter_id)
        chapter.delete()
        return response_builder(
            success=True,
            message="Chapter deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )

class UpdateSLOView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def patch(self, request, slo_id):
        slo = get_object_or_404(SLO, id=slo_id)
        serializer = SLOSerializer(slo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return response_builder(
                success=True,
                message="SLO updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(success=False, message=errors, data=None, status_code=status.HTTP_400_BAD_REQUEST)

class DeleteSLOView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def delete(self, request, slo_id):
        slo = get_object_or_404(SLO, id=slo_id)
        slo.delete()
        return response_builder(
            success=True,
            message="SLO deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )

class ResetAcademicDataView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        password = request.data.get('password')
        if not password:
            return response_builder(
                success=False,
                message="password parameter is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Verify admin's password
        if not request.user.check_password(password):
            return response_builder(
                success=False,
                message="Invalid password verification.",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Local imports to prevent circular imports
        from study_plans.models import StudyPlan, StudyPlanSLO
        from assessments.models import AssessmentModel, Question, StudentAssessment, QuestionBulkUpload

        # Clear data in dependency order to prevent constraint violation errors
        StudyPlanSLO.objects.all().delete()
        StudyPlan.objects.all().delete()
        
        StudentAssessment.objects.all().delete()
        Question.objects.all().delete()
        AssessmentModel.objects.all().delete()
        QuestionBulkUpload.objects.all().delete()
        
        SLO.objects.all().delete()
        Chapter.objects.all().delete()
        Subject.objects.all().delete()
        Grade.objects.all().delete()
        CurriculumBulkUpload.objects.all().delete()

        return response_builder(
            success=True,
            message="All academic data cleared successfully.",
            status_code=status.HTTP_200_OK
        )