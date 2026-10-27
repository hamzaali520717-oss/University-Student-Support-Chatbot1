from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.academics.models import Program
from apps.accounts.models import AdminProfile, StudentProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "date_joined"]
        read_only_fields = fields


class StudentProfileSerializer(serializers.ModelSerializer):
    program = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["registration_no", "program"]


class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = []


class MeSerializer(serializers.Serializer):
    user = UserSerializer()
    profile = serializers.SerializerMethodField()

    def get_profile(self, obj: dict) -> dict | None:
        profile = obj["profile"]
        if profile is None:
            return None
        if isinstance(profile, StudentProfile):
            return StudentProfileSerializer(profile).data
        return AdminProfileSerializer(profile).data


class StudentRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    registration_no = serializers.CharField(max_length=32)
    program = serializers.SlugRelatedField(slug_field="code", queryset=Program.objects.all())

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_registration_no(self, value: str) -> str:
        if StudentProfile.objects.filter(registration_no=value).exists():
            raise serializers.ValidationError("A student with that registration number already exists.")
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["role"] = user.role
        token["user_id"] = user.id
        return token
