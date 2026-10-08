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
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return error_response(
                code="VALIDATION_ERROR",
                message="username, email, dan password wajib diisi.",
                status_code=status.HTTP_400_BAD_REQUEST,
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