from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api_response import success_response, error_response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        fields = serializers.Serializer(data=request.data)
        fields.fields.update({
            "username": serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()]),
            "email": serializers.EmailField(max_length=254),
            "password": serializers.CharField(trim_whitespace=False, write_only=True),
        })
        if not fields.is_valid():
            return error_response(
                code="VALIDATION_ERROR", message="Data registrasi tidak valid.",
                details=fields.errors, status_code=status.HTTP_400_BAD_REQUEST,
            )
        username = fields.validated_data["username"]
        email = fields.validated_data["email"]
        password = fields.validated_data["password"]
        try:
            validate_password(password, User(username=username, email=email))
        except DjangoValidationError as exc:
            return error_response(
                code="VALIDATION_ERROR", message="Password tidak memenuhi persyaratan.",
                details={"password": exc.messages}, status_code=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return error_response(
                code="USERNAME_ALREADY_EXISTS",
                message="Username sudah digunakan.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            return error_response(
                code="EMAIL_ALREADY_EXISTS",
                message="Email sudah digunakan.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        return success_response(
            {
                "message": "Registrasi berhasil.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status_code=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
            }
        )

class LoginView(TokenObtainPairView):

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return error_response(
                code="AUTHENTICATION_FAILED",
                message="Username atau password salah.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return success_response(
            serializer.validated_data
        )