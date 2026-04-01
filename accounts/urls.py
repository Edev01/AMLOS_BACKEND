from django.urls import path
from accounts.views import LoginView, CreateSchoolView, CreateTeacherView, CreateStudentView ,AdminSignupView

urlpatterns = [
    path('admin/signup/', AdminSignupView.as_view(), name='admin-signup'),
    path('login/', LoginView.as_view()),
    path('create-school/', CreateSchoolView.as_view()),
    path('create-teacher/', CreateTeacherView.as_view()),
    path('create-student/', CreateStudentView.as_view()),
]