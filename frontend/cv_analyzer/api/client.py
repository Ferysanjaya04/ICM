import requests
from django.conf import settings

class APIClient:
    def __init__(self):
        self.base_url = settings.BACKEND_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def analyze_cv(self, cv_file, job_description):
        url = f"{self.base_url}/api/analyze/"
        files = {"cv": cv_file}
        data = {"job_description": job_description}
        response = requests.post(url, files=files, data=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_recommendation(self, cv_file):
        url = f"{self.base_url}/api/recommend/"
        files = {"cv": cv_file}
        response = requests.post(url, files=files, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def login(self, username, password):
        url = f"{self.base_url}/api/auth/login/"
        data = {"username": username, "password": password}
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def register(self, username, email, password):
        url = f"{self.base_url}/api/auth/register/"
        data = {"username": username, "email": email, "password": password}
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()
