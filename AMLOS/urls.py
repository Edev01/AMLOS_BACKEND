from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/curriculum/", include("curriculum.urls")),
    path("api/study-plans/", include("study_plans.urls")),
]
