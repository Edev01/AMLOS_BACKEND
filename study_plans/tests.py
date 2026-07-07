from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from curriculum.models import Grade, Subject, Chapter, SLO
from study_plans.models import StudyPlan, StudyPlanSLO

User = get_user_model()

class StudyPlanTimeTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@amlos.com',
            username='admin',
            password='password123',
            role=User.Role.ADMIN
        )
        self.student = User.objects.create_user(
            email='student@amlos.com',
            username='student',
            password='password123',
            role=User.Role.STUDENT
        )
        self.grade = Grade.objects.create(name="Grade 10", description="Grade 10 Description")
        self.subject = Subject.objects.create(name="Mathematics", description="Math Desc", grade="Grade 10")
        self.chapter = Chapter.objects.create(subject=self.subject, name="Chapter 1")
        self.slo = SLO.objects.create(
            chapter=self.chapter,
            slo_no="1.1",
            name="SLO Name",
            difficulty_frequency=SLO.Difficulty.MEDIUM,
            estimated_time=30
        )
        self.admin_token = str(AccessToken.for_user(self.admin))
        self.student_token = str(AccessToken.for_user(self.student))

    def test_create_study_plan_with_single_study_time_daily(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        url = '/api/study-plans/create'
        payload = {
            "title": "Algebra Plan",
            "plan_type": "CUSTOM",
            "grade": "Grade 10",
            "mode": "PARALLEL",
            "start_date": "2026-07-01",
            "end_date": "2026-07-10",
            "study_time_daily": 150,
            "slo_ids": [self.slo.id],
            "skip_weekends": False
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        plan = StudyPlan.objects.get(title="Algebra Plan")
        self.assertEqual(plan.study_time_daily, 150)
        self.assertEqual(plan.min_study_time_daily, 150)
        self.assertEqual(plan.max_study_time_daily, 150)

        # Check detail API output
        detail_url = f'/api/study-plans/{plan.id}'
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['data']['study_time_daily'], 150)
        self.assertNotIn('min_study_time_daily', detail_response.data['data'])
        self.assertNotIn('max_study_time_daily', detail_response.data['data'])
