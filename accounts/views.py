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
from accounts.serializers import *
from rest_framework.permissions import AllowAny
from utils.jwt_utils import get_tokens_for_user 
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

from study_plans.models import StudyPlan

class LoginView(APIView):
    permission_classes = []  

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)

            profile = user.get_profile()   
            profile_data = {}
            if profile:
                
                profile_data = {
                    field.name: getattr(profile, field.attname)
                    for field in profile._meta.fields
                    if field.name != 'id' and field.name != 'user'
                }

            if user.role == "STUDENT":
                is_plan_active = StudyPlan.objects.filter(user=user, status=StudyPlan.Status.ACTIVE).exists()
                profile_data['is_plan_active'] = is_plan_active

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
    allowed_roles = [ 'SCHOOL']

    def post(self, request):
        data = request.data

        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            role='TEACHER'
        )

        return Response({"message": "Teacher created"})
    

class CreateStudentView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['SCHOOL']

    def post(self, request):
        serializer = CreateStudentSerializer(
            data=request.data,
            context={'request': request}
        )
        auth = JWTAuthentication()
        header = auth.get_header(request)
        raw_token = auth.get_raw_token(header)
        validated_token = auth.get_validated_token(raw_token)

        # ✅ Log token payload
        print(f"Decoded Token: {validated_token}")

        # You can also access fields
        print(f"User ID: {validated_token.get('user_id')}")
        print(f"Role: {validated_token.get('role')}")

        if serializer.is_valid():
            student = serializer.save()

            data = {
                "student": {
                    "id": student.id,
                    "username": student.user.username,
                    "email": student.user.email,
                    "roll_number": student.roll_number,
                    "grade": student.grade,
                    "gpa": student.gpa,
                    "school": student.school.school_name
                }
            }

            return response_builder(
                success=True,
                message="Student created successfully",
                data=data,
                status_code=status.HTTP_201_CREATED
            )

        # flatten errors
        errors = " ".join([str(err[0]) for err in serializer.errors.values()])

        return response_builder(
            success=False,
            message=errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
class UpdateStudentView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['SCHOOL']

    def patch(self, request, student_id):
        school = request.user.school_profile

        student = get_object_or_404(Student, id=student_id, school=school)

        serializer = CreateStudentSerializer(
            student,
            data=request.data,
            partial=True, 
            context={'request': request}
        )

        if serializer.is_valid():
            updated_student = serializer.save()

            return response_builder(
                success=True,
                message="Student updated successfully",
                data={
                    "student_id": updated_student.id
                },
                status_code=status.HTTP_200_OK
            )

        return response_builder(
            success=False,
            message=serializer.errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class DeleteStudentView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['SCHOOL']

    def delete(self, request, student_id):
        school = request.user.school_profile

        
        student = get_object_or_404(Student, id=student_id, school=school)
 
        student.user.delete()  

        return response_builder(
            success=True,
            message="Student deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )


class GetAllSchoolsView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def get(self, request):
        schools = School.objects.all()
        serializer = SchoolSerializer(schools, many=True)
        return response_builder(
            success=True,
            message="Schools fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class GetSchoolStudentsView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def get(self, request, school_id):
        school = get_object_or_404(School, id=school_id)
        students = Student.objects.filter(school=school)
        serializer = StudentSerializer(students, many=True)
        return response_builder(
            success=True,
            message=f"Students for {school.school_name} fetched successfully",
            data={
                "school_name": school.school_name,
                "students": serializer.data
            },
            status_code=status.HTTP_200_OK
        )    