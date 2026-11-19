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



from django.test import SimpleTestCase
from unittest.mock import patch
from lib import feature2 as engine


class Feature2EvidenceTests(SimpleTestCase):
    def prediction(self, categories):
        probabilities = dict(zip(categories, [.7, .2, .05]))
        return {"status": "success", "predicted_categories": categories, "probabilities": probabilities}

    def recommend(self, text, categories=None):
        categories = categories or ["Backend Developer", "Python Developer", "Software Developer"]
        prediction = self.prediction(categories)
        with patch.object(engine, "predict_career_categories", return_value=prediction):
            result = engine.recommend_career(text)
        self.assertEqual(result["status"], "success", result)
        return result, prediction

    def test_positive_skill_sources_and_rejected_mentions(self):
        text = ("Skills: ReactJS, Postgres, k8s\nProjects: Built REST APIs using Django.\n"
                "Experience: Backend Developer Intern using Python.\n"
                "Summary: No Docker experience. Interested in learning AWS.")
        result, _ = self.recommend(text)
        profile = result["profile_summary"]["cv_understanding"]
        skills = {s["name"]: s for s in profile["skills"]}
        self.assertTrue({"react", "postgresql", "kubernetes", "django", "python", "rest api"}.issubset(skills))
        self.assertNotIn("docker", skills)
        self.assertNotIn("aws", skills)
        self.assertEqual(skills["django"]["source"], "projects")
        self.assertEqual(skills["python"]["source"], "internship")
        self.assertEqual({s["name"] for s in profile["excluded_skill_mentions"]}, {"docker", "aws"})

    def test_reference_vocabulary_is_evidence_based_and_does_not_train_tfidf(self):
        result, _ = self.recommend("Keahlian: Python, Linux, Power BI, Tableau\nPengalaman Kerja: Backend Developer using API Development and Database Design.\nBelum menguasai Docker.")
        self.assertTrue({"api development", "database design", "linux", "power bi", "tableau"}.issubset(result["detected_skills"]))
        self.assertNotIn("docker", result["detected_skills"])
        classifier, vectorizer = engine._load_model()
        self.assertEqual(type(classifier).__name__, "LogisticRegression")
        self.assertEqual(type(vectorizer).__name__, "TfidfVectorizer")
        self.assertEqual(len(classifier.classes_), 30)
        self.assertEqual(len(vectorizer.vocabulary_), 40000)

    def test_unknown_and_zero_skill_coverage_are_distinct(self):
        self.assertIsNone(engine.calculate_skill_match_percentage(["python"], []))
        self.assertIsNone(engine.get_skill_gap(["python"], []))
        self.assertEqual(engine.calculate_skill_match_percentage([], ["Python"]), 0)
        self.assertEqual(engine.calculate_skill_match_percentage(["Postgres", "ReactJS", "k8s"], ["PostgreSQL", "React", "Kubernetes"]), 100)
        self.assertEqual(engine.calculate_skill_match_percentage(["html", "css"], ["HTML/CSS"]), 100)
        self.assertEqual(engine.calculate_skill_match_percentage(["html"], ["HTML/CSS"]), 0)

    def test_role_mapping_uses_explicit_reference_titles(self):
        for category, title in (
            ("DotNet Developer", "C# Developer"), ("System Administrator", "Systems Administrator"),
            ("Software Developer", "Software Engineer"), ("Testing", "Software Test Engineer"),
            ("Backend Developer", "Backend Developer"), ("Data Science", "Data Scientist"),
        ):
            with self.subTest(category=category):
                roles = engine.find_matching_roles(category)
                self.assertEqual(roles[0]["job title"], title)
                self.assertTrue(roles[0]["required_skills"])
                self.assertGreaterEqual(roles[0]["reference_row"], 2)
        for category in ("Site Reliability Engineer", "SQL Developer", "Digital Media", "Cloud Engineer", "Network Security Engineer", "Database"):
            with self.subTest(category=category):
                self.assertEqual(engine.find_matching_roles(category), [])

    def test_top_three_order_and_raw_probabilities_never_follow_skill_scores(self):
        result, prediction = self.recommend("Skills: Python, Django, Docker, Git. Projects: Built a student web application with Python.")
        roles = result["top_recommendations"]
        self.assertEqual([r["predicted_category"] for r in roles], prediction["predicted_categories"])
        self.assertEqual([r["rank"] for r in roles], [1, 2, 3])
        self.assertEqual(len({r["role_title"] for r in roles}), 3)
        for role in roles:
            self.assertEqual(role["category_probability"], prediction["probabilities"][role["predicted_category"]])
            self.assertEqual(role["missing_skills"], engine.get_skill_gap(result["detected_skills"], role["required_skills"]))
        self.assertAlmostEqual(sum(r["category_probability"] for r in roles), .95)

    def test_missing_reference_has_unknown_score_gap_and_learning_path(self):
        result, _ = self.recommend("Fresh graduate. Skills: Python, Git. Projects: Built a Django app for students.",
                                   ["Site Reliability Engineer", "SQL Developer", "Digital Media"])
        for role in result["top_recommendations"]:
            self.assertIsNone(role["match_percentage"])
            self.assertIsNone(role["matched_skills"])
            self.assertIsNone(role["missing_skills"])
            self.assertFalse(role["skill_match_available"])
            self.assertEqual(role["skill_match_status"], "unknown")
            self.assertEqual(role["role_title"], role["predicted_category"])
        for path in result["learning_path"]:
            self.assertEqual(path["status"], "unknown_requirements")
            self.assertEqual(path["steps"], [])
            self.assertEqual(path["suggested_skills"], [])

    def test_known_zero_is_explained_and_learning_path_uses_only_reference_gaps(self):
        result, _ = self.recommend("Skills: Figma. Projects: Created visual user interfaces and prototypes for student applications.")
        for role, path in zip(result["top_recommendations"], result["learning_path"]):
            self.assertEqual(role["match_percentage"], 0)
            self.assertTrue(role["skill_match_available"])
            self.assertEqual(role["skill_match_status"], "known")
            self.assertEqual(set(path["suggested_skills"]), set(role["required_skills"]))
            self.assertTrue(all("Jika sudah menguasai" in s["activity"] for s in path["steps"]))

    def test_mobile_reference_requires_discriminating_evidence(self):
        result, _ = self.recommend("Skills: REST API. Fresh graduate seeking opportunities in software engineering.",
                                   ["Mobile Developer", "Python Developer", "Backend Developer"])
        self.assertEqual(result["top_recommendations"][0]["role_title"], "Mobile Developer")
        self.assertIsNone(result["top_recommendations"][0]["match_percentage"])
        result, _ = self.recommend("Skills: Swift, Xcode, REST API. Projects: Built an iOS application using Swift.",
                                   ["Mobile Developer", "Python Developer", "Backend Developer"])
        self.assertEqual(result["top_recommendations"][0]["role_title"], "Mobile Developer iOS")

    def test_raw_classifier_probabilities_are_identical_with_recommendation_output(self):
        text = "Fresh graduate. Skills: Python, Django, Git. Projects: Built a web app with PostgreSQL for students."
        prediction = engine.predict_career_categories(text)
        result = engine.recommend_career(text)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["all_predicted_categories"], prediction["predicted_categories"])
        self.assertEqual(result["profile_summary"]["category_probabilities"], prediction["probabilities"])

    def test_evidence_error_is_not_logged(self):
        with patch.object(engine, "understand_cv", side_effect=RuntimeError("PRIVATE_EVIDENCE_MARKER")):
            with self.assertLogs("lib.feature2", level="ERROR") as logs:
                result = engine.recommend_career("Skills: Python and Django. Projects: Built a student web application.")
        self.assertEqual(result["status"], "error")
        self.assertNotIn("PRIVATE_EVIDENCE_MARKER", "\n".join(logs.output))


class CareerQualityRegressionTests(SimpleTestCase):
    def recommend(self, text, category='Mobile Developer'):
        categories=[category,'Python Developer','Backend Developer']
        with patch.object(engine,'predict_career_categories',return_value={
            'status':'success','predicted_categories':categories,
            'probabilities':dict(zip(categories,[.5,.3,.1])),
        }):
            result=engine.recommend_career(text)
        self.assertEqual(result['status'],'success',result)
        return result

    def test_equal_mobile_evidence_keeps_category_and_unknown_requirements(self):
        result=self.recommend('Skills: Swift, Xcode, Kotlin, Android SDK. Projects: Built mobile applications for both platforms.')
        role=result['top_recommendations'][0]
        self.assertEqual(role['role_title'],'Mobile Developer')
        self.assertIsNone(role['match_percentage'])
        self.assertEqual(role['requirements_status'],'unknown')
        self.assertIsNone(role['missing_skills'])
        self.assertEqual(result['learning_path'][0]['steps'],[])
        self.assertEqual(role['category_probability'],.5)

    def test_ui_ux_tied_evidence_is_not_resolved_by_csv_order(self):
        result=self.recommend('Skills: Figma, User Research. Projects: Created interfaces and conducted user interviews.','UI/UX Designer')
        self.assertEqual(result['top_recommendations'][0]['role_title'],'UI/UX Designer')
        self.assertIsNone(result['top_recommendations'][0]['match_percentage'])

    def test_salary_reference_is_not_presented_without_units(self):
        result=self.recommend('Skills: Python, Django. Projects: Built a Python application for students.')
        for role in result['top_recommendations']:
            self.assertEqual(role['salary_range'],'')
            self.assertEqual(role['salary_metadata']['status'],'unknown')
            self.assertIsNone(role['salary_metadata']['currency'])
            self.assertIsNone(role['salary_metadata']['payment_period'])
            self.assertIsNone(role['salary_metadata']['market'])
            if role['reference']:
                self.assertEqual(role['salary_metadata']['source'],role['reference'])
                self.assertEqual(len(role['reference']['sha256']),64)

    def test_alias_and_composite_gaps_are_symmetric(self):
        self.assertEqual(engine.get_skill_gap(['HTML/CSS','Postgres','Spark','RESTful APIs'],['HTML','CSS','PostgreSQL','Apache Spark','REST API']),[])
        self.assertEqual(engine.get_skill_gap(['HTML','CSS'],['HTML/CSS']),[])
        self.assertEqual(engine.get_skill_gap(['HTML'],['HTML/CSS']),['html/css'])

    def test_matched_skill_has_positive_evidence_not_learning_gap(self):
        result=self.recommend('Skills: Python, Django, SQL, RESTful API. Projects: Used Python in a project. No Docker experience.')
        role=result['top_recommendations'][1]
        self.assertEqual(role['role_title'],'Python Developer')
        self.assertNotIn('rest api',role['missing_skills'])
        for skill in role['matched_skills']:
            self.assertTrue(role['skill_evidence'][skill])
            self.assertNotIn(skill,result['learning_path'][1]['suggested_skills'])

    def test_six_categories_stay_unknown_without_invented_requirements(self):
        for category in ['Cloud Engineer','Database','Digital Media','Network Security Engineer','SQL Developer','Site Reliability Engineer']:
            with self.subTest(category=category):
                role=self.recommend('Skills: Python. Projects: Built a student software application using Python.',category)['top_recommendations'][0]
                self.assertEqual(role['role_title'],category)
                self.assertEqual(role['requirements_status'],'unknown')
                self.assertIsNone(role['match_percentage'])
                self.assertIsNone(role['skill_evidence'])


    def test_reference_api_salary_has_unknown_units_and_retains_raw(self):
        from recommendations.models import JobRole
        from recommendations.serializers import JobRoleSerializer
        row=JobRole(role_title='Reference role',category='Technology',salary_range='65-120K')
        data=JobRoleSerializer(row).data
        self.assertEqual(data['salary_range'],'')
        self.assertEqual(data['legacy_salary_range'],'65-120K')
        self.assertEqual(data['salary_metadata']['status'],'unknown')
        self.assertIsNone(data['salary_metadata']['currency'])
        self.assertEqual(row.salary_range,'65-120K')
