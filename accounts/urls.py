from django.urls import path
from accounts.views import  *

urlpatterns = [
    path('admin/signup', AdminSignupView.as_view(), name='admin-signup'),
    path('login', LoginView.as_view()),
    path('school/create', CreateSchoolView.as_view()),
    path('students/create', CreateStudentView.as_view()),
    path('students/<int:student_id>', UpdateStudentView.as_view()),
    path('students/<int:student_id>/delete', DeleteStudentView.as_view()),
    path('create-teacher', CreateTeacherView.as_view()),
    path('schools', GetAllSchoolsView.as_view()),
    path('schools/<int:school_id>/students', GetSchoolStudentsView.as_view()),
]