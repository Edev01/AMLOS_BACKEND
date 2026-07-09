from rest_framework import serializers
from .models import Question, AssessmentModel, StudentAssessment, ExamType, QuestionBulkUpload

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class ExamTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamType
        fields = ['id', 'name', 'grade', 'created_at']
        read_only_fields = ['created_at']

class AssessmentModelSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    chapters_details = serializers.SerializerMethodField(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    exam_type_detail = ExamTypeSerializer(source='exam_type', read_only=True)
    total_questions = serializers.IntegerField(required=False)

    class Meta:
        model = AssessmentModel
        fields = [
            'id', 'title', 'assessment_type', 'grade', 'subject', 'subject_name',
            'chapter_ids', 'chapters_details', 'cognitive_levels', 'cognitive_level_details', 'categories',
            'total_questions', 'mcq_count', 'short_count', 'long_count', 'questions',
            'exam_type', 'exam_type_detail', 'duration_minutes', 'created_at'
        ]

    def get_chapters_details(self, obj):
        return [{'id': ch.id, 'name': ch.name} for ch in obj.chapters.all()]

    def create(self, validated_data):
        chapter_ids = validated_data.pop('chapter_ids', [])
        assessment = AssessmentModel.objects.create(**validated_data)
        assessment.chapters.set(chapter_ids)
        return assessment

class StudentAssessmentSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source='assessment_model.title', read_only=True)
    assessment_type = serializers.CharField(source='assessment_model.assessment_type', read_only=True)
    questions = QuestionSerializer(source='assessment_model.questions', many=True, read_only=True)

    class Meta:
        model = StudentAssessment
        fields = ['id', 'student', 'assessment_model', 'assessment_title', 'assessment_type', 'score', 'total_marks', 'is_completed', 'started_at', 'completed_at', 'submission_file', 'questions']
        read_only_fields = ['student', 'started_at', 'completed_at']

class QuestionBulkUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBulkUpload
        fields = ['id', 'uploaded_file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

