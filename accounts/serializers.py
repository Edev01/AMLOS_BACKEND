# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from accounts.models import User, School, Student, Teacher, PaperCheckerProfile, PaperCheckerAssignment, TestURL
from django.db import transaction
# Admin signup serializer.
from rest_framework import serializers
from django.db import transaction
from accounts.models import User, Admin

def generate_username_suggestion(username):
    if "@" in username:
        local_part, domain = username.split("@", 1)
        counter = 1
        while True:
            candidate = f"{local_part}{counter}@{domain}"
            if not User.objects.filter(username=candidate).exists():
                return candidate
            counter += 1
    else:
        counter = 1
        while True:
            candidate = f"{username}{counter}"
            if not User.objects.filter(username=candidate).exists():
                return candidate
            counter += 1


class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        return token

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        print(email)
        print(password)


        if email and password:
            # Find the user case-insensitively to support case-insensitive email logins
            try:
                user_obj = User.objects.get(email__iexact=email.strip())
                username_to_auth = user_obj.email
            except User.DoesNotExist:
                username_to_auth = email.strip()

            user = authenticate(username=username_to_auth, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
        else:
            raise serializers.ValidationError("Both email and password are required.")

        data['user'] = user
        return data

class AdminSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        with transaction.atomic():

            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                password=validated_data['password'],
                role=User.Role.ADMIN
            )

            Admin.objects.create(user=user)

        return user
    

class CreateSchoolSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField()
    profile_image = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    
    # School fields
    school_name = serializers.CharField(max_length=255)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField()
    website = serializers.URLField(required=False, allow_blank=True)
    established_year = serializers.IntegerField(required=False)
    principal_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            suggestion = generate_username_suggestion(value)
            raise serializers.ValidationError(f"Username already exists, try using @{suggestion}")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_registration_number(self, value):
        if value:
            if School.objects.filter(registration_number=value).exists():
                raise serializers.ValidationError("Registration number already exists.")
        return value

    def create(self, validated_data):
        """
        Create User + School profile in one atomic transaction
        """
        with transaction.atomic():
            profile_image = validated_data.get('profile_image', None)
            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                password=validated_data['password'],
                role=User.Role.SCHOOL,
                profile_image=profile_image,
                created_by=self.context['request'].user
            )

            registration_number = validated_data.get('registration_number')
            if not registration_number:
                import random
                import string
                while True:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    registration_number = f"REG-{code}"
                    if not School.objects.filter(registration_number=registration_number).exists():
                        break

            school = School.objects.create(
                user=user,
                school_name=validated_data['school_name'],
                registration_number=registration_number,
                address=validated_data['address'],
                website=validated_data.get('website', ''),
                established_year=validated_data.get('established_year', None),
                principal_name=validated_data['principal_name'],
                phone=validated_data.get('phone', '')
            )

            return school


class CreateStudentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    profile_image = serializers.URLField(write_only=True, required=False, allow_null=True, allow_blank=True)

    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Student
        fields = [
            'username',
            'password',
            'email',
            'profile_image',
            'enrollment_date',
            'state',
            'first_name', 
            'last_name', 
            'roll_number',
            'grade',
            'section',
            'gender',
            'date_of_birth',
            'guardian_phone',
            'guardian_name',
            'guardian_email'
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            suggestion = generate_username_suggestion(value)
            raise serializers.ValidationError(f"Username already exists, try using @{suggestion}")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        school = request.user.school_profile

        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        profile_image = validated_data.pop('profile_image', None)

        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')

        # ✅ Create User
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role=User.Role.STUDENT,
            first_name=first_name,
            last_name=last_name,
            profile_image=profile_image,
            created_by=request.user
        )

        student = Student.objects.create(
            user=user,
            school=school,
            **validated_data
        )

        return student
    
    def update(self, instance, validated_data):
        user = instance.user
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)
        profile_image = validated_data.pop('profile_image', None)

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            user.email = email
            user.username = email
        if password is not None:
            user.set_password(password)
        if profile_image is not None:
            user.profile_image = profile_image

        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class SchoolSerializer(serializers.ModelSerializer):
    teachers = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_image = serializers.URLField(source='user.profile_image', read_only=True)
    created_at = serializers.DateTimeField(source='user.created_at', read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'school_name', 'registration_number', 'phone', 'address', 'website', 
            'established_year', 'principal_name', 'teachers', 'email', 'profile_image', 'created_at'
        ]
        read_only_fields = ('user',)
        
    def get_teachers(self, obj):
        from .serializers import TeacherSerializer
        teachers = obj.teachers.all()
        return TeacherSerializer(teachers, many=True).data

class StudentSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_image = serializers.URLField(source='user.profile_image', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'email', 
            'profile_image',
            'roll_number', 
            'grade', 
            'section',
            'gender',
            'state',
            'date_of_birth', 
            'enrollment_date',
            'guardian_name',
            'guardian_phone',
            'guardian_email'
        ]


class CreateTeacherSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    profile_image = serializers.URLField(write_only=True, required=False, allow_null=True, allow_blank=True)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Teacher
        fields = [
            'username',
            'password',
            'email',
            'profile_image',
            'first_name',
            'last_name',
            'subject',
            'qualification',
            'experience_years',
            'salary',
            'hire_date'
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            suggestion = generate_username_suggestion(value)
            raise serializers.ValidationError(f"Username already exists, try using @{suggestion}")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        school = request.user.school_profile

        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        profile_image = validated_data.pop('profile_image', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role=User.Role.TEACHER,
            first_name=first_name,
            last_name=last_name,
            profile_image=profile_image,
            created_by=request.user
        )

        teacher = Teacher.objects.create(
            user=user,
            school=school,
            **validated_data
        )

        return teacher

    def update(self, instance, validated_data):
        user = instance.user
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)
        profile_image = validated_data.pop('profile_image', None)

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            user.email = email
            user.username = email
        if password is not None:
            user.set_password(password)
        if profile_image is not None:
            user.profile_image = profile_image

        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class TeacherSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_image = serializers.URLField(source='user.profile_image', read_only=True)
    assigned_students = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'email', 
            'profile_image',
            'subject', 
            'qualification', 
            'experience_years', 
            'salary', 
            'hire_date',
            'assigned_students'
        ]

    def get_assigned_students(self, obj):
        return [{'id': s.id, 'name': f"{s.user.first_name} {s.user.last_name}".strip() or s.user.email} for s in obj.students.all()]

class UpdateSchoolSerializer(serializers.ModelSerializer):
    profile_image = serializers.URLField(write_only=True, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = School
        fields = [
            'school_name',
            'registration_number',
            'phone',
            'address',
            'website',
            'established_year',
            'principal_name',
            'profile_image'
        ]

    def update(self, instance, validated_data):
        profile_image = validated_data.pop('profile_image', None)
        if profile_image is not None:
            instance.user.profile_image = profile_image
            instance.user.save()
        return super().update(instance, validated_data)

class UserRoleManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'profile_image']

class ResetPasswordByRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
    role = serializers.ChoiceField(choices=['SCHOOL', 'TEACHER', 'STUDENT', 'PAPER_CHECKER'], required=True)

class CreatePaperCheckerSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    password = serializers.CharField(write_only=True, min_length=6, required=False)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    profile_image = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        # Password is required only on creation
        if not self.instance and 'password' not in attrs:
            raise serializers.ValidationError({"password": "Password is required for creation."})
        return attrs

    def validate_username(self, value):
        user = getattr(self.instance, 'user', None) if self.instance else None
        qs = User.objects.filter(username=value)
        if user:
            qs = qs.exclude(id=user.id)
        if qs.exists():
            suggestion = generate_username_suggestion(value)
            raise serializers.ValidationError(f"Username already exists, try using @{suggestion}")
        return value

    def validate_email(self, value):
        user = getattr(self.instance, 'user', None) if self.instance else None
        qs = User.objects.filter(email=value)
        if user:
            qs = qs.exclude(id=user.id)
        if qs.exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        from django.db import transaction
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                password=validated_data['password'],
                role=User.Role.PAPER_CHECKER,
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                profile_image=validated_data.get('profile_image'),
                phone=validated_data.get('phone'),
                created_by=self.context['request'].user
            )
            profile = PaperCheckerProfile.objects.create(user=user)
            return profile

    def update(self, instance, validated_data):
        user = instance.user
        email = validated_data.get('email')
        username = validated_data.get('username')
        password = validated_data.get('password')
        first_name = validated_data.get('first_name')
        last_name = validated_data.get('last_name')
        profile_image = validated_data.get('profile_image')
        phone = validated_data.get('phone')

        if email is not None:
            user.email = email
            user.username = email
        if username is not None:
            user.username = username
        if password is not None:
            user.set_password(password)
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if profile_image is not None:
            user.profile_image = profile_image
        if phone is not None:
            user.phone = phone
            
        user.save()
        return instance

class PaperCheckerSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_image = serializers.URLField(source='user.profile_image', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = PaperCheckerProfile
        fields = ['id', 'email', 'first_name', 'last_name', 'profile_image', 'phone']


class TestURLSerializer(serializers.ModelSerializer):
    pageUrl = serializers.CharField(source='page_url', required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = TestURL
        fields = ['id', 'url', 'source', 'pageUrl', 'created_at']