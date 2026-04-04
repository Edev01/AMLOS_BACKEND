from rest_framework.views import APIView
from rest_framework import status
from utils.response_builder import response_builder
from .serializers import SubjectSerializer, ChapterSerializer, SLOSerializer
from accounts.permissions import IsRole
from rest_framework.permissions import IsAuthenticated

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
            message=errors,
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
