from django.db import models

class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=False)
    grade = models.CharField(max_length=20, default="", blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subjects'

    def __str__(self):
        return self.name

class Chapter(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chapters'

    def __str__(self):
        return f"{self.name} - {self.subject.name}"

class SLO(models.Model):
    class Difficulty(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='slos')
    name = models.CharField(max_length=255)
    difficulty_frequency = models.CharField(max_length=10, choices=Difficulty.choices)
    estimated_time = models.IntegerField(help_text="Estimated time in minutes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'slos'

    def __str__(self):
        return self.name
