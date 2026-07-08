import datetime
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from curriculum.models import Subject, Chapter, SLO
from study_plans.models import StudyPlan, StudyPlanSLO
from assessments.models import Question, AssessmentModel, StudentAssessment

User = get_user_model()

class TimedAssessmentTests(APITestCase):

    def setUp(self):
        # Create users
        self.student = User.objects.create_user(
            email='student@amlos.com',
            username='student',
            password='password123',
            role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            email='admin@amlos.com',
            username='admin',
            password='password123',
            role=User.Role.ADMIN
        )

        # Create Subject and Chapter
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Math Description",
            grade="Grade 10"
        )
        self.chapter = Chapter.objects.create(
            subject=self.subject,
            name="Algebra"
        )

        # Create a StudyPlan for Student
        self.study_plan = StudyPlan.objects.create(
            user=self.student,
            grade="Grade 10",
            title="Algebra Plan",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=30),
            status=StudyPlan.Status.ACTIVE
        )

        # Create SLO and StudyPlanSLO to complete chapter and unlock assessment
        self.slo = SLO.objects.create(
            chapter=self.chapter,
            slo_no="1.1",
            name="Solve algebraic equations",
            difficulty_frequency=SLO.Difficulty.MEDIUM,
            estimated_time=45
        )
        self.plan_slo = StudyPlanSLO.objects.create(
            plan=self.study_plan,
            slo=self.slo,
            scheduled_date=timezone.now().date(),
            order_in_day=1,
            subject_name="Mathematics",
            chapter_name="Algebra",
            estimated_time=45,
            is_completed=True
        )

        # Create Assessment Model (with timer)
        self.assessment = AssessmentModel.objects.create(
            title="Timed Math Test",
            assessment_type=AssessmentModel.AssessmentType.CHAPTER_WISE,
            grade="Grade 10",
            subject=self.subject,
            total_questions=1,
            duration_minutes=60
        )
        self.assessment.chapters.add(self.chapter)

        # Generate JWT tokens for authentication
        self.student_token = str(AccessToken.for_user(self.student))
        self.admin_token = str(AccessToken.for_user(self.admin))

    def set_student_auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

    def set_admin_auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

    def test_assessment_detail_starts_timer(self):
        self.set_student_auth()
        url = f'/api/assessments/models/{self.assessment.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify student assessment attempt is created
        attempt = StudentAssessment.objects.filter(student=self.student, assessment_model=self.assessment).first()
        self.assertIsNotNone(attempt)
        
        # Verify returned data contains started_at and time_left_seconds
        data = response.data['data']
        self.assertIn('started_at', data)
        self.assertIn('time_left_seconds', data)
        self.assertIsNotNone(data['time_left_seconds'])
        # Allow small deviation in processing time
        self.assertTrue(3590 <= data['time_left_seconds'] <= 3600)

    def test_submit_within_time_limit(self):
        self.set_student_auth()
        # Open detail first to start timer
        detail_url = f'/api/assessments/models/{self.assessment.id}'
        self.client.get(detail_url)

        # Submit answers
        submit_url = f'/api/assessments/models/{self.assessment.id}/submit'
        payload = {
            'score': 8,
            'total_marks': 10
        }
        response = self.client.post(submit_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        attempt = StudentAssessment.objects.get(student=self.student, assessment_model=self.assessment)
        self.assertTrue(attempt.is_completed)
        self.assertEqual(attempt.score, 8)
        self.assertEqual(attempt.total_marks, 10)

    def test_submit_after_time_limit_expires(self):
        self.set_student_auth()
        # Open detail first to start timer
        detail_url = f'/api/assessments/models/{self.assessment.id}'
        self.client.get(detail_url)

        # Artificially alter the start time in the DB to make it expired (e.g. 2 hours ago)
        attempt = StudentAssessment.objects.get(student=self.student, assessment_model=self.assessment)
        attempt.started_at = timezone.now() - datetime.timedelta(hours=2)
        attempt.save()

        # Try to submit answers
        submit_url = f'/api/assessments/models/{self.assessment.id}/submit'
        payload = {
            'score': 8,
            'total_marks': 10
        }
        response = self.client.post(submit_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Time limit exceeded. This assessment is closed for submissions.")

    def test_available_assessments_includes_timer_info(self):
        self.set_student_auth()
        # Request detail to start timer
        detail_url = f'/api/assessments/models/{self.assessment.id}'
        self.client.get(detail_url)

        # Check available assessments list
        url = '/api/assessments/available'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['data']
        # Find our assessment in results
        matched = [r for r in results if r['id'] == self.assessment.id]
        self.assertEqual(len(matched), 1)
        
        self.assertEqual(matched[0]['duration_minutes'], 60)
        self.assertIsNotNone(matched[0]['started_at'])
        self.assertTrue(3590 <= matched[0]['time_left_seconds'] <= 3600)

    def test_list_all_assessments_includes_questions(self):
        # Create a mock Question and link to the assessment model
        question = Question.objects.create(
            question_id="Q1",
            subject="Mathematics",
            chapter="Chapter 1",
            question_type="MCQ",
            cognitive_level="Knowledge",
            category="Book Exercise",
            question_text="What is 2 + 2?",
            answer_text="4",
            difficulty_level="Easy"
        )
        self.assessment.questions.add(question)

        self.set_admin_auth()
        url = '/api/assessments/models/all'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['data']['results']
        matched = [r for r in results if r['id'] == self.assessment.id]
        self.assertEqual(len(matched), 1)

        # Assert questions are nested and contain correct properties
        self.assertIn('questions', matched[0])
        self.assertEqual(len(matched[0]['questions']), 1)
        self.assertEqual(matched[0]['questions'][0]['question_id'], "Q1")
        self.assertEqual(matched[0]['questions'][0]['question_text'], "What is 2 + 2?")

    def test_create_assessment_with_cognitive_level_details(self):
        # Create candidate questions of different cognitive levels
        q1 = Question.objects.create(
            question_id="Q101",
            subject="Mathematics",
            chapter="Chapter 1",
            question_type="MCQ",
            cognitive_level="Knowledge",
            question_text="Q101 Text",
            answer_text="Ans",
            difficulty_level="Easy"
        )
        q2 = Question.objects.create(
            question_id="Q102",
            subject="Mathematics",
            chapter="Chapter 1",
            question_type="SHORT",
            cognitive_level="Understanding",
            question_text="Q102 Text",
            answer_text="Ans",
            difficulty_level="Medium"
        )

        self.set_admin_auth()
        url = '/api/assessments/models'
        payload = {
            "title": "Detailed Quiz",
            "assessment_type": "CHAPTER_WISE",
            "grade": "Grade 10",
            "subject": self.subject.id,
            "chapter_ids": [self.chapter.id],
            "cognitive_levels": ["Knowledge", "Understanding"],
            "cognitive_level_details": {
                "Knowledge": {
                    "mcq_count": 1,
                    "short_count": 0,
                    "long_count": 0
                },
                "Understanding": {
                    "mcq_count": 0,
                    "short_count": 1,
                    "long_count": 0
                }
            }
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        # Verify computed fields and selected questions
        data = response.data['data']
        self.assertEqual(data['mcq_count'], 1)
        self.assertEqual(data['short_count'], 1)
        self.assertEqual(data['long_count'], 0)
        self.assertEqual(data['total_questions'], 2)
        self.assertEqual(len(data['questions']), 2)
        
        # Verify specific questions selected
        q_ids = [q['question_id'] for q in data['questions']]
        self.assertIn("Q101", q_ids)
        self.assertIn("Q102", q_ids)


from assessments.models import ExamType

class ExamTypeTests(APITestCase):

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
        self.admin_token = str(AccessToken.for_user(self.admin))
        self.student_token = str(AccessToken.for_user(self.student))

    def test_exam_type_crud(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        # 1. Create exam types for different grades
        res1 = self.client.post('/api/assessments/exam-types', {"name": "Mid Term", "grade": "Grade 9"}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        exam_type_id = res1.data['data']['id']

        res2 = self.client.post('/api/assessments/exam-types', {"name": "Final Term", "grade": "Grade 9"}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        res3 = self.client.post('/api/assessments/exam-types', {"name": "Mid Term", "grade": "Grade 10"}, format='json')
        self.assertEqual(res3.status_code, status.HTTP_201_CREATED)

        # 2. List all exam types
        list_all = self.client.get('/api/assessments/exam-types/list')
        self.assertEqual(list_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_all.data['data']), 3)

        # 3. List exam types filtered by grade
        list_g9 = self.client.get('/api/assessments/exam-types/list?grade=Grade 9')
        self.assertEqual(list_g9.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_g9.data['data']), 2)

        list_g10 = self.client.get('/api/assessments/exam-types/list?grade=Grade 10')
        self.assertEqual(list_g10.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_g10.data['data']), 1)

        # 4. Update exam type
        update_res = self.client.patch(f'/api/assessments/exam-types/{exam_type_id}/update', {"name": "Quarter Exam"}, format='json')
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data['data']['name'], "Quarter Exam")

        # 5. Delete exam type
        delete_res = self.client.delete(f'/api/assessments/exam-types/{exam_type_id}/delete')
        self.assertEqual(delete_res.status_code, status.HTTP_200_OK)

        # Verify deletion
        list_after = self.client.get('/api/assessments/exam-types/list?grade=Grade 9')
        self.assertEqual(len(list_after.data['data']), 1)

    def test_duplicate_exam_type_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.client.post('/api/assessments/exam-types', {"name": "Mid Term", "grade": "Grade 9"}, format='json')
        dup = self.client.post('/api/assessments/exam-types', {"name": "Mid Term", "grade": "Grade 9"}, format='json')
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_access_exam_types(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        res = self.client.post('/api/assessments/exam-types', {"name": "Mid Term", "grade": "Grade 9"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res2 = self.client.get('/api/assessments/exam-types/list')
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)

