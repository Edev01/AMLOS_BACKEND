from django.shortcuts import render

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.models import User
from accounts.permissions import IsRole 
from rest_framework.permissions import IsAuthenticated
from utils.response_builder import response_builder
from rest_framework.views import APIView
from rest_framework import status
from accounts.serializers import AdminSignupSerializer, CreateSchoolSerializer , LoginSerializer
from rest_framework.permissions import AllowAny
from utils.jwt_utils import get_tokens_for_user 

class LoginView(APIView):
    permission_classes = []  # public API

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)

            # Get the profile of the user depending on role
            profile = user.get_profile()  # you already have get_profile() in User model
            profile_data = {}
            if profile:
                # Convert profile model to dict
                profile_data = {
                    field.name: getattr(profile, field.name)
                    for field in profile._meta.fields
                    if field.name != 'id' and field.name != 'user'
                }

            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "profile": profile_data
            }

            return response_builder(
                success=True,
                message="Login successful",
                data={
                    "user": user_data,
                    "tokens": tokens
                },
                status_code=status.HTTP_200_OK
            )

        # Flatten errors to string
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )



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
            message = list(serializer.errors.values())[0][0],
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )



class CreateSchoolView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def post(self, request):
        serializer = CreateSchoolSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            school = serializer.save()

            data = {
                "school": {
                    "id": school.id,
                    "school_name": school.school_name,
                    "registration_number": school.registration_number,
                    "address": school.address,
                    "website": school.website,
                    "established_year": school.established_year
                }
            }

            return response_builder(
                success=True,
                message="School created successfully",
                data=data,
                status_code=status.HTTP_201_CREATED
            )

        # If serializer errors
        return response_builder(
            success=False,
            message = list(serializer.errors.values())[0][0],
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )
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