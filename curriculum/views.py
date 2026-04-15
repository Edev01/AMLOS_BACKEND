from rest_framework.views import APIView
from rest_framework import status
from utils.response_builder import response_builder
from .serializers import SubjectSerializer, ChapterSerializer, SLOSerializer
from accounts.permissions import IsRole
from rest_framework.permissions import IsAuthenticated
from .models import *
from django.db.models import Count

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