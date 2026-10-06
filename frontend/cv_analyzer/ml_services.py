"""Placeholder ML services module.

In production this would load SentenceTransformer and TF-IDF models.
For now it returns deterministic mock results so the views can run end-to-end.
"""
import os
import uuid
import time
from datetime import datetime

# Try to load real models; fall back to mocks if not present
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    import joblib
    _HAS_ML = True
except ImportError:
    _HAS_ML = False

# Mock data
MOCK_SKILLS = {
    'Python': ['Python', 'Django', 'Flask', 'FastAPI', 'Pandas'],
    'JavaScript': ['JavaScript', 'TypeScript', 'React', 'Vue', 'Node.js'],
    'Java': ['Java', 'Spring Boot', 'Microservices'],
    'Go': ['Go', 'Gin', 'Echo'],
    'Cloud': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes'],
}

PRESET_ROLES = [
    {'role': 'Backend Engineer', 'skills': ['Python', 'Django', 'REST API', 'PostgreSQL']},
    {'role': 'Frontend Engineer', 'skills': ['JavaScript', 'TypeScript', 'React', 'Tailwind CSS']},
    {'role': 'Fullstack Developer', 'skills': ['Python', 'Django', 'React', 'TypeScript']},
    {'role': 'DevOps Engineer', 'skills': ['Docker', 'Kubernetes', 'AWS', 'CI/CD']},
    {'role': 'Data Engineer', 'skills': ['Python', 'Pandas', 'SQL', 'Airflow']},
    {'role': 'AI/ML Engineer', 'skills': ['Python', 'PyTorch', 'TensorFlow', 'Scikit-learn']},
]


def _extract_skills(text):
    """Extract skills from text using keyword matching."""
    found = []
    for category, skills in MOCK_SKILLS.items():
        for skill in skills:
            if skill.lower() in text.lower():
                found.append(skill)
    return list(set(found)) if found else ['Python', 'Django']


def analyze_cv(cv_path, job_description):
    """Analyze CV against job description."""
    start = time.time()
    try:
        # Read CV text (simplified)
        cv_text = ""
        if os.path.exists(cv_path):
            with open(cv_path, 'r', errors='ignore') as f:
                cv_text = f.read()
        
        cv_skills = _extract_skills(cv_text + ' ' + job_description)
        jd_skills = _extract_skills(job_description)
        
        matched = [s for s in cv_skills if s in jd_skills] or jd_skills[:2]
        missing = [s for s in jd_skills if s not in matched]
        
        # Calculate score
        score = min(0.95, max(0.3, len(matched) / max(len(jd_skills), 1)))
        
        # Determine level
        if score >= 0.8:
            level = 'EXCELLENT'
        elif score >= 0.6:
            level = 'HIGH'
        elif score >= 0.4:
            level = 'MEDIUM'
        else:
            level = 'LOW'
        
        processing_time = int((time.time() - start) * 1000)
        
        return {
            'compatibility_score': round(score, 4),
            'compatibility_level': level,
            'matched_skills': matched,
            'missing_skills': missing,
            'top_roles': [{'role': r['role'], 'score': round(min(0.98, score + 0.1), 4)} for r in PRESET_ROLES[:3]],
            'skill_gap_matched': matched,
            'skill_gap_missing': missing,
            'roadmap': [{'skill': s, 'priority': 'high', 'resources': [f'Learn {s}']} for s in missing[:3]],
            'processing_time_ms': processing_time,
            'analysis_id': str(uuid.uuid4()),
            'analyzed_at': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'compatibility_score': 0.5,
            'compatibility_level': 'MEDIUM',
            'matched_skills': [],
            'missing_skills': [],
            'top_roles': [],
            'skill_gap_matched': [],
            'skill_gap_missing': [],
            'roadmap': [],
            'processing_time_ms': 0,
            'error': str(e)
        }


def recommend_career(cv_path):
    """Recommend career paths based on CV."""
    start = time.time()
    try:
        cv_text = ""
        if os.path.exists(cv_path):
            with open(cv_path, 'r', errors='ignore') as f:
                cv_text = f.read()
        
        cv_skills = _extract_skills(cv_text)
        
        # Score each role
        recommendations = []
        for role_data in PRESET_ROLES:
            overlap = len(set(cv_skills) & set(role_data['skills']))
            score = min(0.98, max(0.3, overlap / len(role_data['skills'])))
            recommendations.append({
                'role': role_data['role'],
                'score': round(score, 4),
                'matched_skills': list(set(cv_skills) & set(role_data['skills'])),
                'missing_skills': list(set(role_data['skills']) - set(cv_skills))
            })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_roles = recommendations[:3]
        
        processing_time = int((time.time() - start) * 1000)
        
        return {
            'compatibility_score': round(top_roles[0]['score'], 4) if top_roles else 0,
            'compatibility_level': 'HIGH' if top_roles and top_roles[0]['score'] > 0.6 else 'MEDIUM',
            'matched_skills': cv_skills,
            'missing_skills': [],
            'top_roles': top_roles,
            'skill_gap_matched': cv_skills,
            'skill_gap_missing': [],
            'roadmap': [],
            'processing_time_ms': processing_time,
            'analysis_id': str(uuid.uuid4()),
            'analyzed_at': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'compatibility_score': 0.5,
            'compatibility_level': 'MEDIUM',
            'matched_skills': [],
            'missing_skills': [],
            'top_roles': [],
            'skill_gap_matched': [],
            'skill_gap_missing': [],
            'roadmap': [],
            'processing_time_ms': 0,
            'error': str(e)
        }