from django.shortcuts import render

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.models import User
from accounts.permissions import IsRole
from utils.response_builder import response_builder
from rest_framework.views import APIView
from rest_framework import status
from accounts.serializers import AdminSignupSerializer
from rest_framework.permissions import AllowAny
from utils.jwt_utils import get_tokens_for_user 

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer



class AdminSignupView(APIView):
    permission_classes = [AllowAny]  # public API

    def post(self, request):
        serializer = AdminSignupSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            tokens = get_tokens_for_user(user)

            return response_builder(
                success=True,
                message="Admin created successfully",
                data={
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "role": user.role
                    },
                    "tokens": tokens
                },
                status_code=status.HTTP_201_CREATED
            )

        return response_builder(
            success=False,
            message="Validation error",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )



class CreateSchoolView(APIView):
    permission_classes = [IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        data = request.data

        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            role='SCHOOL'
        )

        return Response({"message": "School created"})    
    

class CreateTeacherView(APIView):
    permission_classes = [IsRole]
    allowed_roles = ['ADMIN', 'SCHOOL']

    def post(self, request):
        data = request.data

        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            role='TEACHER'
        )

        return Response({"message": "Teacher created"})
    
class CreateStudentView(APIView):
    permission_classes = [IsRole]
    allowed_roles = ['SCHOOL']

    def post(self, request):
        data = request.data

        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            role='USER'
        )

        return Response({"message": "Student created"})