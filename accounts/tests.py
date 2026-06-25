from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import School, Student, Teacher

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
