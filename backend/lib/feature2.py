"""
Feature 2: Career Recommendation Engine
Modul AI untuk merekomendasikan jalur karier berdasarkan CV.

Pipeline:
1. Load pre-trained TF-IDF + Logistic Regression model
2. Load job roles reference data
3. Extract & normalize CV text
4. Predict top-3 career categories
5. Match skills dengan job requirements
6. Generate recommendations dengan explanations
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
import unicodedata

import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS & PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
# Data files are in VitLog/data/, not backend/data/
# Go up two levels: lib/ -> backend/ -> VitLog/
VITLOG_ROOT = BASE_DIR.parent.parent
MODEL_PATH = VITLOG_ROOT / "data" / "processed" / "job_role_classifier.joblib"
JOB_ROLES_PATH = VITLOG_ROOT / "data" / "raw" / "job_roles.csv"
SKILLS_DB_PATH = BASE_DIR / "skills_database.json"

# ============================================================
# GLOBAL STATE (Lazy loading)
# ============================================================

_classifier = None
_vectorizer = None
_job_roles_df = None
_skills_database = None


def _load_model():
    """Load pre-trained model dan vectorizer dari joblib."""
    global _classifier, _vectorizer

    if _classifier is not None and _vectorizer is not None:
        return _classifier, _vectorizer

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model tidak ditemukan: {MODEL_PATH}")

    try:
        model_package = joblib.load(str(MODEL_PATH))

        # Expected format: dict with 'pipeline' key
        if isinstance(model_package, dict) and 'pipeline' in model_package:
            pipeline = model_package['pipeline']

            # Extract tfidf and classifier from pipeline steps
            if hasattr(pipeline, 'named_steps'):
                _vectorizer = pipeline.named_steps.get('tfidf')
                _classifier = pipeline.named_steps.get('classifier')
            else:
                # Fallback: assume pipeline is (tfidf, classifier)
                if isinstance(pipeline, tuple) and len(pipeline) == 2:
                    _vectorizer, _classifier = pipeline
        elif isinstance(model_package, dict):
            # Legacy: separate classifier dan vectorizer
            _classifier = model_package.get('classifier')
            _vectorizer = model_package.get('vectorizer')
        else:
            # Assume it's a pipeline directly
            if hasattr(model_package, 'named_steps'):
                _vectorizer = model_package.named_steps.get('tfidf')
                _classifier = model_package.named_steps.get('classifier')
            else:
                _classifier = model_package

        if _classifier is None:
            raise ValueError("Classifier tidak ditemukan dalam model package")
        if _vectorizer is None:
            raise ValueError("Vectorizer tidak ditemukan dalam model package")

        logger.info("Model berhasil dimuat")
        return _classifier, _vectorizer

    except Exception as e:
        logger.error(f"Gagal memuat model: {e}")
        raise


def _load_job_roles():
    """Load job roles reference dari CSV."""
    global _job_roles_df

    if _job_roles_df is not None:
        return _job_roles_df

    if not JOB_ROLES_PATH.exists():
        raise FileNotFoundError(f"Job roles CSV tidak ditemukan: {JOB_ROLES_PATH}")

    try:
        _job_roles_df = pd.read_csv(str(JOB_ROLES_PATH))

        # Normalize column names
        _job_roles_df.columns = [col.lower().strip() for col in _job_roles_df.columns]

        logger.info(f"Job roles dimuat: {len(_job_roles_df)} entries")
        return _job_roles_df

    except Exception as e:
        logger.error(f"Gagal memuat job roles: {e}")
        raise


def _load_skills_database():
    """Load skills database dari JSON."""
    global _skills_database

    if _skills_database is not None:
        return _skills_database

    if not SKILLS_DB_PATH.exists():
        logger.warning(f"Skills database tidak ditemukan: {SKILLS_DB_PATH}, menggunakan fallback")
        _skills_database = {"default": []}
        return _skills_database

    try:
        with open(str(SKILLS_DB_PATH)) as f:
            _skills_database = json.load(f)

        logger.info(f"Skills database dimuat: {len(_skills_database)} categories")
        return _skills_database

    except Exception as e:
        logger.error(f"Gagal memuat skills database: {e}")
        _skills_database = {"default": []}
        return _skills_database


# ============================================================
# TEXT PROCESSING FUNCTIONS
# ============================================================

def normalize_text(text: str) -> str:
    """Normalize text: unicode, lowercase, whitespace."""
    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize("NFKC", str(text))

    # Lowercase
    text = text.lower()

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_skills_from_text(text: str, skills_db: Dict) -> List[str]:
    """Extract skills dari teks CV berdasarkan skills database."""
    normalized_text = normalize_text(text)
    found_skills = set()

    # Flatten all skills dari semua categories
    all_skills = []
    for category, skills in skills_db.items():
        if isinstance(skills, list):
            all_skills.extend(skills)
        elif isinstance(skills, dict):
            # Handle nested structure
            for subcategory, subskills in skills.items():
                if isinstance(subskills, list):
                    all_skills.extend(subskills)

    # Match skills dalam teks
    for skill in all_skills:
        skill_normalized = normalize_text(skill)
        # Simple word boundary matching
        if re.search(rf"\b{re.escape(skill_normalized)}\b", normalized_text):
            found_skills.add(skill_normalized)

    return sorted(list(found_skills))


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict_career_categories(cv_text: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Predict top-k career categories dari CV text.

    Args:
        cv_text: Teks CV yang sudah diekstrak
        top_k: Jumlah kategori top yang dikembalikan

    Returns:
        Dict dengan predictions, probabilities, dan metadata
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text tidak boleh kosong")

    try:
        classifier, vectorizer = _load_model()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "predictions": [],
            "probabilities": {}
        }

    try:
        # Normalize CV text
        cv_normalized = normalize_text(cv_text)

        # Vectorize
        cv_features = vectorizer.transform([cv_normalized])

        # Predict probabilities
        probabilities = classifier.predict_proba(cv_features)[0]
        classes = classifier.classes_

        # Get top-k
        top_indices = np.argsort(probabilities)[-top_k:][::-1]

        predictions = []
        prob_dict = {}

        for idx in top_indices:
            category = classes[idx]
            prob = float(probabilities[idx])
            predictions.append(category)
            prob_dict[category] = prob

        return {
            "status": "success",
            "predicted_categories": predictions,
            "probabilities": prob_dict,
            "top_category": predictions[0] if predictions else None
        }

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "predictions": [],
            "probabilities": {}
        }


# ============================================================
# JOB MATCHING & SKILL GAP FUNCTIONS
# ============================================================

def find_matching_roles(predicted_category: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Find matching job roles untuk predicted category.

    Strategy:
    1. Try exact match on job_title (case-insensitive)
    2. If no exact match, try keyword matching
    3. If still no match, search in category column
    """
    try:
        job_roles = _load_job_roles()
    except Exception as e:
        logger.error(f"Gagal load job roles: {e}")
        return []

    roles = []

    # Strategy 1: Exact match on job_title (primary method)
    matching_roles = job_roles[
        job_roles['job title'].str.contains(predicted_category, case=False, na=False)
    ].head(top_n)

    if len(matching_roles) > 0:
        logger.info(f"Found {len(matching_roles)} roles by exact title match for '{predicted_category}'")
        for _, row in matching_roles.iterrows():
            role_dict = row.to_dict()
            if isinstance(role_dict.get('required_skills'), str):
                try:
                    role_dict['required_skills'] = json.loads(role_dict['required_skills'])
                except:
                    role_dict['required_skills'] = []
            roles.append(role_dict)
        return roles

    # Strategy 2: Keyword matching for fuzzy cases
    # Extract keywords from predicted_category
    keywords = predicted_category.split()
    for keyword in keywords:
        if len(keyword) > 2:  # Skip very short words
            matching_roles = job_roles[
                job_roles['job title'].str.contains(keyword, case=False, na=False)
            ].head(top_n)

            if len(matching_roles) > 0:
                logger.info(f"Found {len(matching_roles)} roles by keyword '{keyword}' for '{predicted_category}'")
                for _, row in matching_roles.iterrows():
                    role_dict = row.to_dict()
                    if isinstance(role_dict.get('required_skills'), str):
                        try:
                            role_dict['required_skills'] = json.loads(role_dict['required_skills'])
                        except:
                            role_dict['required_skills'] = []
                    roles.append(role_dict)
                return roles[:top_n]  # Limit to top_n

    # Strategy 3: Fallback to category column (for very different input)
    if predicted_category.lower() not in [cat.lower() for cat in job_roles['category'].unique()]:
        logger.warning(f"Category '{predicted_category}' not found in job titles or categories")
        return []

    matching_roles = job_roles[
        job_roles['category'].str.lower() == predicted_category.lower()
    ].head(top_n)

    for _, row in matching_roles.iterrows():
        role_dict = row.to_dict()
        if isinstance(role_dict.get('required_skills'), str):
            try:
                role_dict['required_skills'] = json.loads(role_dict['required_skills'])
            except:
                role_dict['required_skills'] = []
        roles.append(role_dict)

    return roles


def calculate_skill_match_percentage(cv_skills: List[str], required_skills: List[str]) -> float:
    """Calculate match percentage antara CV skills dan required skills."""
    if not required_skills:
        return 100.0

    cv_skills_set = set(s.lower() for s in cv_skills)
    required_set = set(s.lower() for s in required_skills)

    matched = len(cv_skills_set & required_set)
    total = len(required_set)

    return round((matched / total) * 100, 2) if total > 0 else 0.0


def get_skill_gap(cv_skills: List[str], required_skills: List[str]) -> List[str]:
    """Get missing skills (skill gap)."""
    cv_skills_set = set(s.lower() for s in cv_skills)
    required_set = set(s.lower() for s in required_skills)

    gap = required_set - cv_skills_set
    return sorted(list(gap))


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def recommend_career(cv_text: str) -> Dict[str, Any]:
    """
    Main function untuk generate career recommendations dari CV.

    Args:
        cv_text: Teks CV yang sudah diekstrak dari file

    Returns:
        Dict dengan struktur recommendation yang siap disimpan ke database
        {
            "status": "success" | "error",
            "error": str (jika status error),
            "predicted_category": str,
            "top_recommendations": [
                {
                    "rank": int,
                    "role_title": str,
                    "category": str,
                    "match_percentage": float,
                    "required_skills": list,
                    "salary_range": str
                },
                ...
            ],
            "detected_skills": list,
            "skill_gaps": dict (role -> gap list),
            "profile_summary": dict
        }
    """
    if not cv_text or not cv_text.strip():
        return {
            "status": "error",
            "error": "CV text tidak boleh kosong"
        }

    # Step 1: Load skills database
    try:
        skills_db = _load_skills_database()
    except Exception as e:
        return {
            "status": "error",
            "error": f"Gagal load skills database: {e}"
        }

    # Step 2: Extract skills dari CV
    detected_skills = extract_skills_from_text(cv_text, skills_db)

    # Step 3: Predict career categories
    prediction_result = predict_career_categories(cv_text, top_k=3)

    if prediction_result["status"] != "success":
        return {
            "status": "error",
            "error": prediction_result.get("error", "Prediction failed")
        }

    predicted_categories = prediction_result["predicted_categories"]
    predicted_category = predicted_categories[0] if predicted_categories else None

    if not predicted_category:
        return {
            "status": "error",
            "error": "Tidak dapat memprediksi kategori karier dari CV"
        }

    # Step 4: Find matching roles for ALL top-3 predicted categories
    all_matching_roles = []
    seen_titles = set()

    for cat_idx, cat in enumerate(predicted_categories):
        cat_prob = prediction_result["probabilities"].get(cat, 0.0)
        matching_roles = find_matching_roles(cat, top_n=3)

        for role in matching_roles:
            job_title = role.get('job title', role.get('role_title', 'Unknown'))
            # Deduplicate by job title
            if job_title not in seen_titles:
                # Add category probability as a weight for sorting
                role['_source_category'] = cat
                role['_source_category_prob'] = cat_prob
                role['_category_rank'] = cat_idx
                all_matching_roles.append(role)
                seen_titles.add(job_title)

    if not all_matching_roles:
        return {
            "status": "warning",
            "message": f"Tidak ada job roles ditemukan untuk kategori top-3: {predicted_categories}",
            "predicted_category": predicted_category,
            "all_predicted_categories": predicted_categories,
            "detected_skills": detected_skills,
            "top_recommendations": [],
            "profile_summary": {}
        }

    # Sort by: category rank (top predicted category first), then by match percentage
    all_matching_roles.sort(key=lambda r: (r.get('_category_rank', 99), -calculate_skill_match_percentage(detected_skills, r.get('required_skills', []))))

    # Take top 3 overall
    top_matching_roles = all_matching_roles[:3]

    # Step 5: Calculate match percentages dan skill gaps
    top_recommendations = []
    skill_gaps = {}

    for rank, role in enumerate(top_matching_roles, 1):
        required_skills = role.get('required_skills', [])
        # Handle both 'required_skills' (underscore) dan 'required skills' (space)
        if not required_skills:
            required_skills = role.get('required skills', [])

        if isinstance(required_skills, str):
            # Parse pipe-separated skills dari CSV
            if '|' in required_skills:
                required_skills = [s.strip() for s in required_skills.split('|')]
            else:
                try:
                    required_skills = json.loads(required_skills)
                except:
                    required_skills = []

        match_pct = calculate_skill_match_percentage(detected_skills, required_skills)
        gap = get_skill_gap(detected_skills, required_skills)

        # Get job_title (CSV uses 'job title' with space after normalization)
        job_title = role.get('job title', role.get('role_title', 'Unknown'))

        # Get salary_range (CSV uses 'salary range' with space after normalization)
        salary_range = role.get('salary range', role.get('salary_range', ''))

        # Get category from CSV (more accurate than predicted)
        category = role.get('category', role.get('_source_category', predicted_category))

        # Get description (fallback if available)
        description = role.get('description', '')

        top_recommendations.append({
            "rank": rank,
            "role_title": job_title,
            "category": category,
            "match_percentage": match_pct,
            "required_skills": required_skills,
            "salary_range": salary_range,
            "description": description
        })

        skill_gaps[job_title] = gap

    # Step 6: Create profile summary
    profile_summary = {
        "cv_length": len(cv_text),
        "detected_skills_count": len(detected_skills),
        "top_category": predicted_category,
        "all_predicted_categories": predicted_categories,
        "category_probabilities": prediction_result.get("probabilities", {})
    }

    return {
        "status": "success",
        "predicted_category": predicted_category,
        "top_recommendations": top_recommendations,
        "detected_skills": detected_skills,
        "skill_gaps": skill_gaps,
        "profile_summary": profile_summary
    }


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def validate_cv_text(cv_text: str, min_length: int = 50) -> Tuple[bool, str]:
    """Validate CV text untuk processing."""
    if not cv_text:
        return False, "CV text tidak boleh kosong"

    if len(cv_text.strip()) < min_length:
        return False, f"CV text terlalu pendek (minimum {min_length} karakter)"

    return True, "OK"


def reset_cache():
    """Reset global model cache (untuk testing)."""
    global _classifier, _vectorizer, _job_roles_df, _skills_database
    _classifier = None
    _vectorizer = None
    _job_roles_df = None
    _skills_database = None


if __name__ == "__main__":
    # Simple test
    test_cv = """
    Senior Software Engineer dengan 5+ tahun pengalaman di backend development.
    Keahlian: Python, Django, PostgreSQL, AWS, Docker, Kubernetes.
    Pengalaman dengan microservices dan REST API development.
    """

    result = recommend_career(test_cv)
    print(json.dumps(result, indent=2, ensure_ascii=False))