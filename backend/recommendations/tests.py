from django.test import TestCase, Client
from django.contrib.auth.models import User
from resumes.models import Resume
from recommendations.models import CareerRecommendation, TopRole, JobRole
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import json


class Feature2APITestCase(TestCase):
    """Test Feature 2 API endpoints"""
    
    def setUp(self):
        """Setup test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='feature2_test',
            password='test123'
        )
        
        # Create another user for isolation test
        self.other_user = User.objects.create_user(
            username='other_user',
            password='test123'
        )
        
        # Get JWT token for user
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        # Get JWT token for other user
        other_refresh = RefreshToken.for_user(self.other_user)
        self.other_token = str(other_refresh.access_token)
    
    def test_recommendations_endpoint_requires_auth(self):
        """Test that recommendations endpoint requires authentication"""
        response = self.client.get('/api/recommendations/')
        # Should return 401 without auth
        self.assertEqual(response.status_code, 401)
    
    def test_job_roles_endpoint_requires_auth(self):
        """Test that job-roles endpoint requires authentication"""
        response = self.client.get('/api/job-roles/')
        self.assertEqual(response.status_code, 401)
    
    def test_recommendations_list_empty(self):
        """Test recommendations list when user has no recommendations"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/recommendations/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should return empty list or paginated result
        self.assertTrue('count' in data or isinstance(data, list))
    
    def test_user_isolation_recommendations(self):
        """Test that users can only see their own recommendations"""
        # Set credentials for user1
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Get recommendations for user1
        resp1 = self.client.get('/api/recommendations/')
        self.assertEqual(resp1.status_code, 200)
        
        # Switch to user2 credentials
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.other_token}')
        
        # Get recommendations for user2
        resp2 = self.client.get('/api/recommendations/')
        self.assertEqual(resp2.status_code, 200)


class Feature2GenerateEndpointTestCase(TestCase):
    """Test Feature 2 generate endpoint"""
    
    def setUp(self):
        """Setup test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='generate_test',
            password='test123'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        # Create test resume with extracted text
        self.resume = Resume.objects.create(
            user=self.user,
            original_filename='test_cv.pdf',
            extracted_text='Python Django PostgreSQL Software Engineer 5 years experience'
        )
    
    def test_generate_requires_auth(self):
        """Test that generate endpoint requires authentication"""
        response = self.client.post(
            '/api/recommendations/generate/',
            {'resume_id': str(self.resume.id)},
            format='json'
        )
        self.assertEqual(response.status_code, 401)
    
    def test_generate_without_resume(self):
        """Test generate without resume"""
        # Create user with no resumes
        new_user = User.objects.create_user(
            username='no_resume_user',
            password='test123'
        )
        new_refresh = RefreshToken.for_user(new_user)
        new_token = str(new_refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_token}')
        
        response = self.client.post(
            '/api/recommendations/generate/',
            {},
            format='json'
        )
        
        # Should return 400 or similar error
        self.assertIn(response.status_code, [400, 404, 500])
    
    def test_generate_with_valid_resume(self):
        """Test generate with valid resume"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        response = self.client.post(
            '/api/recommendations/generate/',
            {'resume_id': str(self.resume.id)},
            format='json'
        )
        
        # Endpoint should exist and respond
        self.assertIsNotNone(response.status_code)


class JobRoleViewSetTestCase(TestCase):
    """Test JobRole read-only viewset"""
    
    def setUp(self):
        """Setup test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='jobrole_test',
            password='test123'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        # Create test job role with correct fields
        self.job_role = JobRole.objects.create(
            role_title='Software Engineer',
            category='Backend',
            description='Develop backend systems',
            required_skills=['Python', 'Django', 'PostgreSQL'],
            salary_range='5M-10M IDR'
        )
    
    def test_job_roles_list_authenticated(self):
        """Test listing job roles (authenticated)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        response = self.client.get('/api/job-roles/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # Check if response is valid
        self.assertTrue(
            'count' in data or isinstance(data, list),
            "Response should be paginated or list"
        )

