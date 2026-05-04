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
                    "established_year": school.established_year,
                    "principal_name": school.principal_name
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
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['SCHOOL']

    def post(self, request):
        serializer = CreateTeacherSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            teacher = serializer.save()

            data = {
                "teacher": {
                    "id": teacher.id,
                    "username": teacher.user.username,
                    "email": teacher.user.email,
                    "subject": teacher.subject,
                    "school": teacher.school.school_name
                }
            }

            return response_builder(
                success=True,
                message="Teacher created successfully",
                data=data,
                status_code=status.HTTP_201_CREATED
            )

        errors = " ".join([str(err[0]) for err in serializer.errors.values()])
        return response_builder(
            success=False,
            message=errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class UpdateTeacherView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['SCHOOL']

    def patch(self, request, teacher_id):
        school = request.user.school_profile
        teacher = get_object_or_404(Teacher, id=teacher_id, school=school)

        serializer = CreateTeacherSerializer(
            teacher,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            updated_teacher = serializer.save()

            return response_builder(
                success=True,
                message="Teacher updated successfully",
                data={"teacher_id": updated_teacher.id},
                status_code=status.HTTP_200_OK
            )

        return response_builder(
            success=False,
            message=serializer.errors,
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class DeleteTeacherView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['SCHOOL']

    def delete(self, request, teacher_id):
        school = request.user.school_profile
        teacher = get_object_or_404(Teacher, id=teacher_id, school=school)
        
        teacher.user.delete()
        
        return response_builder(
            success=True,
            message="Teacher deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )

class GetAllTeachersView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN', 'SCHOOL']

    def get(self, request):
        if request.user.role == 'SCHOOL':
            teachers = Teacher.objects.filter(school=request.user.school_profile)
        else:
            teachers = Teacher.objects.all()
            
        serializer = TeacherSerializer(teachers, many=True)
        return response_builder(
            success=True,
            message="Teachers fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    

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


class UpdateSchoolView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def patch(self, request, school_id):
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return response_builder(
                success=False,
                message="School not found",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateSchoolSerializer(
            school,
            data=request.data,
            partial=True  
        )

        if serializer.is_valid():
            serializer.save()

            return response_builder(
                success=True,
                message="School updated successfully",
                data={
                    "school": serializer.data
                },
                status_code=status.HTTP_200_OK
            )

        return response_builder(
            success=False,
            message=list(serializer.errors.values())[0][0],
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class DeleteSchoolView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = ['ADMIN']

    def delete(self, request, school_id):
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return response_builder(
                success=False,
                message="School not found",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )

        user = school.user

        school.delete()
        user.delete() 

        return response_builder(
            success=True,
            message="School deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK
        )