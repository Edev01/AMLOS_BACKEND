from django.contrib.auth.models import AbstractUser
from django.db import models

 
class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        SCHOOL = 'SCHOOL', 'School'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
        HR = 'HR', 'HR'
        FINANCE = 'FINANCE', 'Finance'
        PAPER_CHECKER = 'PAPER_CHECKER', 'Paper Checker'

  
    email = models.EmailField(unique=True, db_index=True)

    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)

    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.URLField(max_length=500, null=True, blank=True, help_text="S3 URL of the user's profile image")

    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    fcm_token = models.CharField(max_length=255, null=True, blank=True)


  
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 

    class Meta:
        db_table = "users"

    def get_profile(self):
        return {
            self.Role.ADMIN: getattr(self, 'admin_profile', None),
            self.Role.SCHOOL: getattr(self, 'school_profile', None),
            self.Role.TEACHER: getattr(self, 'teacher_profile', None),
            self.Role.STUDENT: getattr(self, 'student_profile', None),
            self.Role.HR: getattr(self, 'hr_profile', None),
            self.Role.FINANCE: getattr(self, 'finance_profile', None),
            self.Role.PAPER_CHECKER: getattr(self, 'paper_checker_profile', None),
        }.get(self.role)

    def __str__(self):
        return f"{self.email} ({self.role})"

 
class School(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='school_profile'
    )

    school_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)

    address = models.TextField()
    website = models.URLField(blank=True)

    established_year = models.IntegerField(null=True, blank=True)
    principal_name = models.CharField(max_length=255,null =True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "schools"

    def __str__(self):
        return self.school_name
 
class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='students',
        db_index=True
    )

    roll_number = models.CharField(max_length=50, unique=True)
    grade = models.CharField(max_length=20)
    section = models.CharField(max_length=20, null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)

    enrollment_date = models.DateField(auto_now_add=True)
    
    guardian_name = models.CharField(max_length=255, null=True, blank=True)
    guardian_phone = models.CharField(max_length=15, null=True, blank=True)
    guardian_email = models.EmailField(null=True, blank=True)

    class Meta:
        db_table = "students"

    def __str__(self):
        return f"{self.user.email} - {self.roll_number}"
 
class Teacher(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='teachers',
        db_index=True
    )

    subject = models.CharField(max_length=100)
    qualification = models.CharField(max_length=255)
    experience_years = models.IntegerField(default=0)

    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hire_date = models.DateField(auto_now_add=True)
    students = models.ManyToManyField(Student, related_name='assigned_teachers', blank=True)

    class Meta:
        db_table = "teachers"

    def __str__(self):
        return f"{self.user.email} - {self.subject}"
 
class Admin(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile'
    )

    access_level = models.CharField(max_length=50, default='SUPER')

    class Meta:
        db_table = "admin"

    def __str__(self):
        return f"{self.user.email} ({self.access_level})"

class HRProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='hr_profile'
    )

    class Meta:
        db_table = "hr_profile"

    def __str__(self):
        return f"{self.user.email} (HR)"

class FinanceProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='finance_profile'
    )

    class Meta:
        db_table = "finance_profile"

    def __str__(self):
        return f"{self.user.email} (Finance)"

class PaperCheckerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='paper_checker_profile'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "paper_checker_profiles"

    def __str__(self):
        return f"{self.user.email} (Paper Checker)"

class PaperCheckerAssignment(models.Model):
    paper_checker = models.ForeignKey(
        PaperCheckerProfile,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    subject = models.ForeignKey(
        'curriculum.Subject',
        on_delete=models.CASCADE,
        related_name='paper_checker_assignments'
    )
    students = models.ManyToManyField(
        'accounts.Student',
        related_name='paper_checker_assignments',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "paper_checker_assignments"
        unique_together = ('paper_checker', 'subject')

    def __str__(self):
        return f"Checker {self.paper_checker.user.email} - Subject {self.subject.name}"


class TestURL(models.Model):
    url = models.TextField()
    source = models.TextField(null=True, blank=True)
    page_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "test_urls"

    def __str__(self):
        return f"TestURL: {self.url[:50]}"