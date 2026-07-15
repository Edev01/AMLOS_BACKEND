from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from curriculum.models import Grade, Subject, Chapter, SLO, CurriculumBulkUpload
from assessments.models import AssessmentModel, Question, StudentAssessment
from study_plans.models import StudyPlan, StudyPlanSLO

User = get_user_model()

class AcademicResetTests(APITestCase):

    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(
            email='admin@amlos.com',
            username='admin',
            password='password123',
            role=User.Role.ADMIN
        )
        self.school = User.objects.create_user(
            email='school@amlos.com',
            username='school',
            password='password123',
            role=User.Role.SCHOOL
        )

        # Create dummy curriculum data
        self.grade = Grade.objects.create(name="Grade 10", description="Grade 10 Description")
        self.subject = Subject.objects.create(name="Math", description="Math Desc", grade="Grade 10")
        self.chapter = Chapter.objects.create(subject=self.subject, name="Algebra")
        self.slo = SLO.objects.create(
            chapter=self.chapter,
            slo_no="1.1",
            name="SLO Name",
            difficulty_frequency=SLO.Difficulty.MEDIUM,
            estimated_time=30
        )

        # Create Assessment and Submissions
        self.assessment = AssessmentModel.objects.create(
            title="Algebra Test",
            assessment_type=AssessmentModel.AssessmentType.CHAPTER_WISE,
            grade="Grade 10",
            subject=self.subject,
            total_questions=1
        )
        self.submission = StudentAssessment.objects.create(
            student=self.school, # Just a user link
            assessment_model=self.assessment,
            is_completed=True,
            score=8,
            total_marks=10
        )

        # Create Study Plan
        self.study_plan = StudyPlan.objects.create(
            user=self.school,
            grade="Grade 10",
            title="My Plan",
            start_date="2026-07-01",
            end_date="2026-07-31"
        )
        self.plan_slo = StudyPlanSLO.objects.create(
            plan=self.study_plan,
            slo=self.slo,
            scheduled_date="2026-07-02",
            order_in_day=1,
            subject_name="Math",
            chapter_name="Algebra",
            estimated_time=30
        )

        # Tokens
        self.admin_token = str(AccessToken.for_user(self.admin))
        self.school_token = str(AccessToken.for_user(self.school))

    def test_admin_resets_data_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = '/api/curriculum/reset-academic-data'
        payload = {"password": "password123"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "All academic data cleared successfully.")

        # Assert all tables are empty
        self.assertEqual(StudyPlanSLO.objects.count(), 0)
        self.assertEqual(StudyPlan.objects.count(), 0)
        self.assertEqual(StudentAssessment.objects.count(), 0)
        self.assertEqual(AssessmentModel.objects.count(), 0)
        self.assertEqual(SLO.objects.count(), 0)
        self.assertEqual(Chapter.objects.count(), 0)
        self.assertEqual(Subject.objects.count(), 0)
        self.assertEqual(Grade.objects.count(), 0)

    def test_admin_resets_data_incorrect_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = '/api/curriculum/reset-academic-data'
        payload = {"password": "wrong_password"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])

        # Assert tables are not cleared
        self.assertEqual(Subject.objects.count(), 1)
        self.assertEqual(Grade.objects.count(), 1)

    def test_school_resets_data_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.school_token}')
        url = '/api/curriculum/reset-academic-data'
        payload = {"password": "password123"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_grade_cascades_curriculum(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Verify initial count
        self.assertEqual(Grade.objects.count(), 1)
        self.assertEqual(Subject.objects.count(), 1)
        self.assertEqual(Chapter.objects.count(), 1)
        self.assertEqual(SLO.objects.count(), 1)
        self.assertEqual(AssessmentModel.objects.count(), 1)
        self.assertEqual(StudyPlanSLO.objects.count(), 1)
        
        # Call Delete Grade View
        url = f'/api/curriculum/grades/{self.grade.id}/delete'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "Grade and all its curriculum data deleted successfully")

        # Verify cascade deletion
        self.assertEqual(Grade.objects.count(), 0)
        self.assertEqual(Subject.objects.count(), 0)
        self.assertEqual(Chapter.objects.count(), 0)
        self.assertEqual(SLO.objects.count(), 0)
        self.assertEqual(AssessmentModel.objects.count(), 0)
        self.assertEqual(StudyPlanSLO.objects.count(), 0)

