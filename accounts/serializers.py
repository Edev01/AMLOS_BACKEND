# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from accounts.models import User, School
from django.db import transaction
# Admin signup serializer.
from rest_framework import serializers
from django.db import transaction
from accounts.models import User, Admin

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
            user = authenticate(username=email, password=password)
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
    
    # School fields
    school_name = serializers.CharField(max_length=255)
    registration_number = serializers.CharField(max_length=100)
    address = serializers.CharField()
    website = serializers.URLField(required=False, allow_blank=True)
    established_year = serializers.IntegerField(required=False)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_registration_number(self, value):
        if School.objects.filter(registration_number=value).exists():
            raise serializers.ValidationError("Registration number already exists.")
        return value

    def create(self, validated_data):
        """
        Create User + School profile in one atomic transaction
        """
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['email'],
                email=validated_data['email'],
                password=validated_data['password'],
                role=User.Role.SCHOOL,
                created_by=self.context['request'].user
            )

            school = School.objects.create(
                user=user,
                school_name=validated_data['school_name'],
                registration_number=validated_data['registration_number'],
                address=validated_data['address'],
                website=validated_data.get('website', ''),
                established_year=validated_data.get('established_year', None)
            )

            return school

class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user    