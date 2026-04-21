from django.db import models
from django.conf import settings
from curriculum.models import SLO
from django.utils import timezone

class StudyPlan(models.Model):
    class PlanType(models.TextChoices):
        RECOMMENDED = 'RECOMMENDED', 'Recommended'
        CUSTOM = 'CUSTOM', 'Custom'

    class Mode(models.TextChoices):
        SEQUENTIAL = 'SEQUENTIAL', 'Sequential'
        PARALLEL = 'PARALLEL', 'Parallel'
        CUSTOM = 'CUSTOM', 'Custom'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_plans')
    plan_type = models.CharField(max_length=20, choices=PlanType.choices, default=PlanType.CUSTOM)
    grade = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=200)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.PARALLEL)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    # New Time Limits
    min_study_time_daily = models.IntegerField(default=120) 
    max_study_time_daily = models.IntegerField(default=300) 

    #streak variable
    current_streak = models.IntegerField(default=0)
    last_streak_date = models.DateField(null=True, blank=True)
    
    
    # Recalculation tracking
    is_completable = models.BooleanField(default=True)
    last_recalculated_at = models.DateField(auto_now_add=True)
    
    custom_pattern = models.JSONField(null=True, blank=True)
    subject_order = models.JSONField(null=True, blank=True) # Now supports nested lists for phases
    
    total_slo_time = models.IntegerField(default=0)
    total_available_time = models.IntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'study_plans'

    def __str__(self):
        return self.title

class StudyPlanSLO(models.Model):
    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='scheduled_slos')
    slo = models.ForeignKey(SLO, on_delete=models.CASCADE)
    scheduled_date = models.DateField()
    order_in_day = models.IntegerField()
    
    # Denormalized for convenience
    subject_name = models.CharField(max_length=100)
    chapter_name = models.CharField(max_length=200)
    estimated_time = models.IntegerField()
    
    
    # Progress tracking
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'study_plan_slos'
        ordering = ['scheduled_date', 'order_in_day']

    def __str__(self):
        return f"{self.plan.title} - {self.slo.name} on {self.scheduled_date}"
