import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAuthentication:

    def setup_method(self):
        self.client = APIClient()

    def test_register_success(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "testuser",
                "email": "testuser@example.com",
                "password": "Test12345!",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == "success"
        assert response.data["data"]["user"]["username"] == "testuser"

        assert User.objects.filter(
            username="testuser"
        ).exists()

    def test_register_duplicate_username(self):
        User.objects.create_user(
            username="testuser",
            email="old@example.com",
            password="Test12345!",
        )

        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "testuser",
                "email": "new@example.com",
                "password": "Test12345!",
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["status"] == "error"
        assert (
            response.data["error"]["code"]
            == "USERNAME_ALREADY_EXISTS"
        )

    def test_login_success(self):
        User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Test12345!",
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "testuser",
                "password": "Test12345!",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "success"
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]

    def test_login_invalid_password(self):
        User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Test12345!",
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "testuser",
                "password": "PasswordSalah123",
            },
            format="json",
        )

        assert response.status_code == 401
        assert response.data["status"] == "error"
        assert (
            response.data["error"]["code"]
            == "AUTHENTICATION_FAILED"
        )

    def test_me_authenticated(self):
        user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Test12345!",
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "testuser",
                "password": "Test12345!",
            },
            format="json",
        )

        access_token = response.data["data"]["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get("/api/auth/me/")

        assert response.status_code == 200
        assert response.data["status"] == "success"
        assert response.data["data"]["username"] == "testuser"