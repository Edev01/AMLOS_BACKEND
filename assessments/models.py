from django.db import models
from django.conf import settings
from curriculum.models import Subject, Chapter

class Question(models.Model):
    question_id = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    chapter = models.CharField(max_length=200)
    question_type = models.CharField(max_length=50) # MCQ, SHORT, LONG
    cognitive_level = models.CharField(max_length=100) # Knowledge, Understanding, Application
    category = models.CharField(max_length=100) # Past Paper, Book Exercise, Additional Question, Conceptual
    question_text = models.TextField()
    question_image_url = models.URLField(max_length=500, null=True, blank=True)
    option_a = models.TextField(null=True, blank=True)
    option_b = models.TextField(null=True, blank=True)
    option_c = models.TextField(null=True, blank=True)
    option_d = models.TextField(null=True, blank=True)
    correct_option = models.CharField(max_length=10, null=True, blank=True) # A, B, C, D
    short_explanation = models.TextField(null=True, blank=True)
    answer_text = models.TextField()
    answer_image_url = models.URLField(max_length=500, null=True, blank=True)
    marks = models.IntegerField(default=1)
    time_allowed_minutes = models.IntegerField(default=1)
    difficulty_level = models.CharField(max_length=50) # Easy, Medium, Hard
    tags = models.TextField(blank=True, default="") # comma separated tags

    class Meta:
        db_table = 'questions'
        unique_together = ('subject', 'question_id')

    def __str__(self):
        return f"{self.subject} - {self.question_id} - {self.question_text[:50]}"


class ExamType(models.Model):
    name = models.CharField(max_length=100)
    grade = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exam_types'
        unique_together = ('name', 'grade')

    def __str__(self):
        return f"{self.name} ({self.grade})"


class AssessmentModel(models.Model):
    class AssessmentType(models.TextChoices):
        CHAPTER_WISE = 'CHAPTER_WISE', 'Chapter-wise'
        QUARTER = 'QUARTER', 'Quarter'
        HALF = 'HALF', 'Half'
        THIRD_QUARTER = 'THIRD_QUARTER', 'Third Quarter'
        FULL_BOOK = 'FULL_BOOK', 'Full Book'

    title = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=50, choices=AssessmentType.choices)
    grade = models.CharField(max_length=20)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assessments')
    chapters = models.ManyToManyField(Chapter, related_name='assessments')
    cognitive_levels = models.JSONField(default=list) # e.g. ["Knowledge", "Understanding"]
    cognitive_level_details = models.JSONField(default=dict, blank=True, null=True)
    categories = models.JSONField(default=list) # e.g. ["Conceptual", "Past Paper"]
    total_questions = models.IntegerField()
    mcq_count = models.IntegerField(default=0)
    short_count = models.IntegerField(default=0)
    long_count = models.IntegerField(default=0)
    questions = models.ManyToManyField(Question, related_name='assessments', blank=True)
    exam_type = models.ForeignKey(ExamType, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duration in minutes. Leave blank/null for no time limit.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assessment_models'

    def __str__(self):
        return f"{self.title} ({self.get_assessment_type_display()})"


class StudentAssessment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assessment_attempts')
    assessment_model = models.ForeignKey(AssessmentModel, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    submission_file = models.FileField(upload_to='assessment_submissions/', null=True, blank=True)

    class Meta:
        db_table = 'student_assessments'
        unique_together = ('student', 'assessment_model')

    def __str__(self):
        return f"{self.student.username} - {self.assessment_model.title} - Score: {self.score}/{self.total_marks}"


class QuestionBulkUpload(models.Model):
    uploaded_file = models.FileField(upload_to='question_bulk_uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'question_bulk_uploads'

    def __str__(self):
        return f"Question Bulk Upload at {self.uploaded_at}"

