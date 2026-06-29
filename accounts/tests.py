from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import School, Student, Teacher
from assessments.models import StudentAssessment, AssessmentModel

User = get_user_model()

class ProfileImageUploadTests(APITestCase):

    def setUp(self):
        # Create an authenticated user
        self.user = User.objects.create_user(
            email='testuser@amlos.com',
            username='testuser',
            password='password123',
            role=User.Role.SCHOOL
        )
        self.token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_upload_image_successfully(self):
        # Create a mock image file
        mock_image = SimpleUploadedFile(
            name='profile.png',
            content=b'mock_image_binary_content',
            content_type='image/png'
        )

        response = self.client.post(
            '/api/auth/upload-image',
            {'image': mock_image},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('url', response.data['data'])
        self.assertIn('path', response.data['data'])
        self.assertTrue(response.data['data']['path'].startswith('profile_images/'))

    def test_upload_no_file_fails(self):
        response = self.client.post(
            '/api/auth/upload-image',
            {},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "No image or file provided. Use key 'image' or 'file'.")


class ProfileImageAccountIntegrationTests(APITestCase):

    def setUp(self):
        # Create ADMIN user
        self.admin_user = User.objects.create_user(
            email='admin@amlos.com',
            username='admin',
            password='password123',
            role=User.Role.ADMIN
        )
        # Create SCHOOL user
        self.school_user = User.objects.create_user(
            email='school@amlos.com',
            username='school',
            password='password123',
            role=User.Role.SCHOOL
        )
        self.school_profile = School.objects.create(
            user=self.school_user,
            school_name="Test School",
            registration_number="REG-MAIN",
            address="123 Main St",
            principal_name="Principal Main"
        )

        self.admin_token = str(AccessToken.for_user(self.admin_user))
        self.school_token = str(AccessToken.for_user(self.school_user))

    def test_create_school_with_profile_image(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        payload = {
            "username": "newschool@amlos.com",
            "password": "password123",
            "email": "newschool@amlos.com",
            "school_name": "New School",
            "registration_number": "REG-NEW",
            "address": "456 Side St",
            "principal_name": "Dr. New Principal",
            "profile_image": "https://s3.amazonaws.com/amlos/profile_images/school.png"
        }
        response = self.client.post('/api/auth/school/create', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['school']['profile_image'], "https://s3.amazonaws.com/amlos/profile_images/school.png")

        # Verify in DB
        created_user = User.objects.get(email="newschool@amlos.com")
        self.assertEqual(created_user.profile_image, "https://s3.amazonaws.com/amlos/profile_images/school.png")

    def test_create_student_with_profile_image(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.school_token}')
        payload = {
            "username": "newstudent@amlos.com",
            "password": "password123",
            "email": "newstudent@amlos.com",
            "first_name": "John",
            "last_name": "Doe",
            "roll_number": "ROLL-STUD-1",
            "grade": "Grade 9",
            "profile_image": "https://s3.amazonaws.com/amlos/profile_images/student.png"
        }
        response = self.client.post('/api/auth/students/create', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['student']['profile_image'], "https://s3.amazonaws.com/amlos/profile_images/student.png")

        # Verify in DB
        created_user = User.objects.get(email="newstudent@amlos.com")
        self.assertEqual(created_user.profile_image, "https://s3.amazonaws.com/amlos/profile_images/student.png")

    def test_create_teacher_with_profile_image(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.school_token}')
        payload = {
            "username": "newteacher@amlos.com",
            "password": "password123",
            "email": "newteacher@amlos.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "subject": "Mathematics",
            "qualification": "Master of Education",
            "profile_image": "https://s3.amazonaws.com/amlos/profile_images/teacher.png"
        }
        response = self.client.post('/api/auth/create-teacher', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['teacher']['profile_image'], "https://s3.amazonaws.com/amlos/profile_images/teacher.png")

        # Verify in DB
        created_user = User.objects.get(email="newteacher@amlos.com")
        self.assertEqual(created_user.profile_image, "https://s3.amazonaws.com/amlos/profile_images/teacher.png")


class TeacherStudentAssignmentTests(APITestCase):

    def setUp(self):
        # Create School
        self.school_user = User.objects.create_user(
            email='school@amlos.com',
            username='school',
            password='password123',
            role=User.Role.SCHOOL
        )
        self.school_profile = School.objects.create(
            user=self.school_user,
            school_name="Test School",
            registration_number="REG-MAIN",
            address="123 Main St",
            principal_name="Principal Main"
        )

        # Create Teacher
        self.teacher_user = User.objects.create_user(
            email='teacher@amlos.com',
            username='teacher',
            password='password123',
            role=User.Role.TEACHER
        )
        self.teacher_profile = Teacher.objects.create(
            user=self.teacher_user,
            school=self.school_profile,
            subject="Maths",
            qualification="B.Sc"
        )

        # Create Student 1 (Assigned)
        self.student_user1 = User.objects.create_user(
            email='student1@amlos.com',
            username='student1',
            password='password123',
            role=User.Role.STUDENT
        )
        self.student_profile1 = Student.objects.create(
            user=self.student_user1,
            school=self.school_profile,
            roll_number="S1",
            grade="Grade 10"
        )

        # Create Student 2 (Unassigned)
        self.student_user2 = User.objects.create_user(
            email='student2@amlos.com',
            username='student2',
            password='password123',
            role=User.Role.STUDENT
        )
        self.student_profile2 = Student.objects.create(
            user=self.student_user2,
            school=self.school_profile,
            roll_number="S2",
            grade="Grade 10"
        )

        # Create Subject
        from curriculum.models import Subject
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Math Description",
            grade="Grade 10"
        )

        # Create Assessment
        self.assessment = AssessmentModel.objects.create(
            title="Algebra Final",
            assessment_type=AssessmentModel.AssessmentType.CHAPTER_WISE,
            grade="Grade 10",
            subject=self.subject,
            total_questions=5
        )

        # Create submissions for both students
        self.submission1 = StudentAssessment.objects.create(
            student=self.student_user1,
            assessment_model=self.assessment,
            is_completed=True,
            score=0,
            total_marks=100
        )
        self.submission2 = StudentAssessment.objects.create(
            student=self.student_user2,
            assessment_model=self.assessment,
            is_completed=True,
            score=0,
            total_marks=100
        )

        self.school_token = str(AccessToken.for_user(self.school_user))
        self.teacher_token = str(AccessToken.for_user(self.teacher_user))

    def test_school_assigns_students_to_teacher(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.school_token}')
        url = f'/api/auth/teachers/{self.teacher_profile.id}/assign-students'
        
        # Test assigning Student 1
        payload = {"student_ids": [self.student_profile1.id]}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['assigned_student_ids'], [self.student_profile1.id])

        # Test listing teacher profile shows assigned students
        get_url = '/api/auth/teachers'
        response_list = self.client.get(get_url)
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)
        teachers = response_list.data['data']
        matched = [t for t in teachers if t['id'] == self.teacher_profile.id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(len(matched[0]['assigned_students']), 1)
        self.assertEqual(matched[0]['assigned_students'][0]['id'], self.student_profile1.id)

    def test_teacher_submission_visibility_and_grading(self):
        # First assign Student 1 to Teacher
        self.teacher_profile.students.add(self.student_profile1)

        # Authenticate as Teacher
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.teacher_token}')

        # 1. Fetch submissions. The teacher should only see submission 1 (assigned student)
        submissions_url = '/api/assessments/submissions'
        response = self.client.get(submissions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        # The teacher should only see submission1 (Student 1) and NOT submission2
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.submission1.id)

        # 2. Grade Submission 1 (Should succeed)
        grade_url1 = f'/api/assessments/submissions/{self.submission1.id}/grade'
        grade_payload = {"score": 85}
        response_grade1 = self.client.patch(grade_url1, grade_payload, format='json')
        self.assertEqual(response_grade1.status_code, status.HTTP_200_OK)
        self.assertTrue(response_grade1.data['success'])
        self.assertEqual(response_grade1.data['data']['score'], 85)

        # 3. Grade Submission 2 (Should fail with 403 Forbidden since Student 2 is not assigned)
        grade_url2 = f'/api/assessments/submissions/{self.submission2.id}/grade'
        response_grade2 = self.client.patch(grade_url2, grade_payload, format='json')
        self.assertEqual(response_grade2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response_grade2.data['success'])
        self.assertEqual(response_grade2.data['message'], "You are not authorized to grade this student's submission.")
