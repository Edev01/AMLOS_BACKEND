from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        SCHOOL = 'SCHOOL', 'School'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(max_length=20, choices=Role.choices)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    # profile_image = models.ImageField(upload_to='profile_image/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users'
    )

    # Link to school (for students & teachers)
    school = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='school_users'
    )

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student')

    roll_number = models.CharField(max_length=50, unique=True)
    grade = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)

    gpa = models.FloatField(null=True, blank=True)
    enrollment_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Student: {self.user.username}"
    
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher')

    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=255)
    experience_years = models.IntegerField(default=0)

    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hire_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Teacher: {self.user.username}"
    
class School(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='school_profile')

    school_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)

    address = models.TextField()
    website = models.URLField(blank=True)

    established_year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.school_name
    
class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin')

    access_level = models.CharField(max_length=50, default='SUPER')

    def __str__(self):
        return f"Admin: {self.user.username}"