from rest_framework import serializers
from .models import Subject, Chapter, SLO

class SubjectSerializer(serializers.ModelSerializer):
    chapter_count = serializers.IntegerField(read_only=True)
    topic_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'grade', 'created_at', 'chapter_count', 'topic_count']

class SLOSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLO
        fields = [
            'id', 'chapter', 'slo_no', 'name', 'difficulty_frequency', 'estimated_time',
            'form_of_assessment', 'remarks', 'google_drive_link', 'google_site', 'priority_score', 'created_at'
        ]

class ChapterSerializer(serializers.ModelSerializer):
    slos = SLOSerializer(many=True, read_only=True)
    topic_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'subject', 'name', 'created_at', 'slos', 'topic_count']

from .models import CurriculumBulkUpload

class CurriculumBulkUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumBulkUpload
        fields = ['id', 'grade', 'uploaded_file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

from .models import Grade

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']
