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
            
            fcm_token = request.data.get('fcm_token')
            if fcm_token:
                user.fcm_token = fcm_token
                user.save(update_fields=['fcm_token'])
                
            tokens = get_tokens_for_user(user)

            profile = user.get_profile()   
            profile_data = {}
            if profile:
                for field in profile._meta.fields:
                    if field.name in ('id', 'user'):
                        continue
                    value = getattr(profile, field.attname)
                    # Serialize date/datetime objects to strings
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    profile_data[field.name] = value

            if user.role == "STUDENT":
                is_plan_active = StudyPlan.objects.filter(user=user, status=StudyPlan.Status.ACTIVE).exists()
                profile_data['is_plan_active'] = is_plan_active
                if profile:
                    profile_data['member_since'] = (
                        profile.enrollment_date.strftime('%Y')
                        if profile.enrollment_date
                        else str(user.date_joined.year)
                    )

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
        user = teacher.user
        
        teacher.delete()
        if user:
            user.delete()

        return response_builder(
            success=True,
            message="Teacher and associated user deleted successfully",
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

class GetAllStudentsView(APIView):
    permission_classes = [IsAuthenticated, IsRole]
    allowed_roles = [ 'SCHOOL']

    def get(self, request):
        school = request.user.school_profile
        students = Student.objects.filter(school=school)
        serializer = StudentSerializer(students, many=True)
        return response_builder(
            success=True,
            message="Students fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
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
        user = student.user
 
        student.delete()
        if user:
            user.delete()

        return response_builder(
            success=True,
            message="Student and associated user deleted successfully",
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


class RequestPasswordResetView(APIView):
    permission_classes = []  # Public endpoint

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import EmailMultiAlternatives

        email = request.data.get('email', '').strip()
        if not email:
            return response_builder(
                success=False,
                message="Email address is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return response_builder(
                success=False,
                message="No account found with this email address.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Generate secure recovery credentials
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Construct the web redirection URL dynamically based on the request's origin host
        scheme = 'https' if request.is_secure() else 'http'
        redirect_web_url = f"{scheme}://{request.get_host()}/api/auth/password-reset/redirect?token={token}&uid={uid}"
        
        # Deep link format (kept for dynamic app launches & emulator copying)
        reset_url = f"amlos://reset-password?token={token}&uid={uid}"

        # Premium HTML Branded email
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reset Your Password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8F9FD; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #F8F9FD; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" max-width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #EAF0FA;">
          
          <!-- Header Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #2168F6 0%, #7D39F1 100%); padding: 40px 30px; text-align: center; color: #ffffff;">
              <h1 style="margin: 0; font-size: 28px; font-weight: 800; letter-spacing: 0.5px;">Account Recovery</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.85;">AMLOS Learning Platform</p>
            </td>
          </tr>
          
          <!-- Content Body -->
          <tr>
            <td style="padding: 40px 30px; color: #1D1F2A; line-height: 1.6;">
              <!-- Brand Logo Pill -->
              <div style="text-align: center; margin-bottom: 30px;">
                <span style="background: linear-gradient(135deg, #2168F6 0%, #7D39F1 100%); color: white; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 24px; font-weight: 800; padding: 10px 22px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 10px rgba(33, 104, 246, 0.2);">
                  AMLOS
                </span>
              </div>
              
              <p style="font-size: 16px; margin-top: 0;">Hi <strong>{user.username}</strong>,</p>
              <p style="font-size: 15px; color: #4A4D5C;">We received a request to reset your password for your AMLOS account. No changes have been made yet.</p>
              <p style="font-size: 15px; color: #4A4D5C;">Please tap the button below to securely reset your password on your mobile device. This secure link is only valid for a limited time.</p>
              
              <!-- Action Button -->
              <div style="text-align: center; margin: 35px 0;">
                <a href="{redirect_web_url}" style="background: linear-gradient(135deg, #2168F6 0%, #7D39F1 100%); color: #ffffff; text-decoration: none; padding: 16px 36px; border-radius: 16px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 8px 20px rgba(33, 104, 246, 0.3);">
                  Reset Password 🔑
                </a>
              </div>
              
              <p style="font-size: 13px; color: #7F8494; text-align: center; margin-bottom: 25px;">
                If tapping the button above does not automatically launch your app, copy and paste this link in your app's test emulator:<br>
                <strong style="color: #2168F6; word-break: break-all;">{reset_url}</strong>
              </p>
              
              <hr style="border: 0; border-top: 1px solid #EAF0FA; margin: 30px 0;">
              
              <p style="font-size: 13px; color: #7F8494; margin-bottom: 0;">If you didn't request a password reset, you can safely ignore this email. Your password will remain completely secure.</p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #F8F9FD; padding: 25px 30px; text-align: center; font-size: 12px; color: #7F8494; border-top: 1px solid #EAF0FA;">
              <p style="margin: 0;">© 2026 AMLOS Education. All rights reserved.</p>
              <p style="margin: 5px 0 0 0; font-size: 11px; opacity: 0.7;">This is an automated notification. Please do not reply to this email.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        text_content = f"Hi {user.username},\n\nUse the following link to reset your AMLOS password:\n{reset_url}"

        # Send multi-part HTML email
        msg = EmailMultiAlternatives(
            subject="Reset your AMLOS Password 🔑",
            body=text_content,
            from_email="noreply@amlos.com",
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return response_builder(
            success=True,
            message="Recovery link sent successfully to your email.",
            data={
                "uid": uid,
                "token": token
            },
            status_code=status.HTTP_200_OK
        )


class ConfirmPasswordResetView(APIView):
    permission_classes = []  # Public endpoint

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str

        uidb64 = request.data.get('uid', '')
        token = request.data.get('token', '')
        new_password = request.data.get('password', '')

        if not uidb64 or not token or not new_password:
            return response_builder(
                success=False,
                message="Missing required parameters (uid, token, or password).",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return response_builder(
                success=False,
                message="Invalid or expired reset token link.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return response_builder(
                success=False,
                message="Password reset link is invalid or has expired.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return response_builder(
            success=True,
            message="Your password has been successfully reset! You can now log in.",
            data=None,
            status_code=status.HTTP_200_OK
        )


from django.http import HttpResponse

class PasswordResetRedirectView(APIView):
    permission_classes = []  # Public endpoint

    def get(self, request):
        token = request.GET.get('token', '')
        uid = request.GET.get('uid', '')
        deep_link = f"amlos://reset-password?token={token}&uid={uid}"
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Opening AMLOS App</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #13141C;
      color: #FFFFFF;
      font-family: 'Segoe UI', Roboto, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }}
    .card {{
      background-color: #1D1F2A;
      padding: 40px 30px;
      border-radius: 24px;
      text-align: center;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      max-width: 400px;
      width: 90%;
      border: 1px solid rgba(255,255,255,0.05);
    }}
    .logo {{
      background: linear-gradient(135deg, #2168F6 0%, #7D39F1 100%);
      color: white;
      font-weight: 800;
      font-size: 28px;
      padding: 12px 24px;
      border-radius: 14px;
      display: inline-block;
      margin-bottom: 25px;
      letter-spacing: 1px;
    }}
    h2 {{
      margin: 0 0 10px 0;
      font-size: 22px;
      font-weight: 700;
    }}
    p {{
      color: rgba(255,255,255,0.7);
      font-size: 14px;
      margin: 0 0 30px 0;
      line-height: 1.5;
    }}
    .btn {{
      background: linear-gradient(135deg, #2168F6 0%, #7D39F1 100%);
      color: white;
      text-decoration: none;
      font-weight: bold;
      padding: 16px 32px;
      border-radius: 16px;
      display: inline-block;
      margin-bottom: 20px;
      box-shadow: 0 5px 15px rgba(33, 104, 246, 0.3);
      font-size: 15px;
    }}
    .copy-box {{
      background-color: rgba(255,255,255,0.05);
      border-radius: 12px;
      padding: 12px;
      font-family: monospace;
      font-size: 12px;
      word-break: break-all;
      border: 1px solid rgba(255,255,255,0.1);
      margin-top: 10px;
      color: #2168F6;
    }}
  </style>
  <script>
    window.onload = function() {{
      // Try to open the app automatically using the deep link scheme
      window.location.href = "{deep_link}";
    }};
  </script>
</head>
<body>
  <div class="card">
    <div class="logo">AMLOS</div>
    <h2>Opening AMLOS App... 🚀</h2>
    <p>We are redirecting you to your secure password reset screen. If the app does not launch automatically, tap the button below:</p>
    <a href="{deep_link}" class="btn">Open App Directly</a>
    <p style="margin: 20px 0 5px 0; font-size: 12px; color: rgba(255,255,255,0.5);">🧪 Developer Test Link:</p>
    <div class="copy-box">{deep_link}</div>
  </div>
</body>
</html>"""
        return HttpResponse(html_content, content_type='text/html')