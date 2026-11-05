
"""
Feature 2: IT Career Recommendation Engine.

Metode utama:
- TF-IDF + Logistic Regression (model pretrained)
- Top-3 kategori karier berdasarkan probabilitas classifier
- Referensi pekerjaan dari job_roles.csv
- Skill matching, skill gap, dan learning path sederhana

Probabilitas classifier dan persentase skill matching
merupakan dua ukuran yang berbeda.
"""

import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
VITLOG_ROOT = BASE_DIR.parent.parent

MODEL_PATH = (
    VITLOG_ROOT / "data" / "processed" /
    "job_role_classifier.joblib"
)
JOB_ROLES_PATH = (
    VITLOG_ROOT / "data" / "raw" / "job_roles.csv"
)
SKILLS_DB_PATH = BASE_DIR / "skills_database.json"

_classifier = None
_vectorizer = None
_job_roles_df = None
_skills_database = None

GENERIC_ROLE_WORDS = {
    "developer", "engineer", "specialist", "analyst",
    "administrator", "consultant", "software",
    "senior", "junior", "lead", "it"
}

ROLE_ALIASES = {
    "back end": "backend",
    "front end": "frontend",
    "full stack": "fullstack",
    "full-stack": "fullstack",
    "dot net": "dotnet",
    ".net": "dotnet",
    "ui ux": "uiux",
    "ui/ux": "uiux",
    "user experience": "uiux",
    "user interface": "uiux",
    "dev ops": "devops",
    "data scientist": "datascience",
    "data science": "datascience",
    "machine learning": "machinelearning",
    "quality assurance": "qa",
    "site reliability": "sre",
    "cyber security": "cybersecurity",
}


def normalize_text(text: str) -> str:
    if text is None:
        return ""

    text = unicodedata.normalize("NFKC", str(text))
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def normalize_role_title(title: str) -> str:
    text = normalize_text(title)

    for original, replacement in sorted(
        ROLE_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        text = text.replace(original, replacement)

    text = re.sub(r"[^a-z0-9+#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_model():
    global _classifier, _vectorizer

    if _classifier is not None and _vectorizer is not None:
        return _classifier, _vectorizer

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Model Feature 2 tidak ditemukan: {MODEL_PATH}"
        )

    # Hanya muat joblib yang berasal dari proyek/sumber tepercaya.
    package = joblib.load(MODEL_PATH)

    if isinstance(package, dict):
        pipeline = package.get("pipeline")

        if pipeline is None:
            classifier = package.get("classifier")
            vectorizer = package.get("vectorizer")
        else:
            if not hasattr(pipeline, "named_steps"):
                raise ValueError(
                    "Format pipeline pada model tidak didukung."
                )
            classifier = pipeline.named_steps.get("classifier")
            vectorizer = pipeline.named_steps.get("tfidf")
    elif hasattr(package, "named_steps"):
        classifier = package.named_steps.get("classifier")
        vectorizer = package.named_steps.get("tfidf")
    else:
        raise ValueError("Format model Feature 2 tidak dikenali.")

    if classifier is None or vectorizer is None:
        raise ValueError(
            "Classifier atau TF-IDF vectorizer tidak ditemukan."
        )

    if not hasattr(classifier, "predict_proba"):
        raise ValueError(
            "Classifier tidak menyediakan predict_proba()."
        )

    _classifier = classifier
    _vectorizer = vectorizer

    logger.info("Model Feature 2 berhasil dimuat.")
    return _classifier, _vectorizer


def _load_job_roles():
    global _job_roles_df

    if _job_roles_df is not None:
        return _job_roles_df

    if not JOB_ROLES_PATH.is_file():
        raise FileNotFoundError(
            f"Data pekerjaan tidak ditemukan: {JOB_ROLES_PATH}"
        )

    df = pd.read_csv(JOB_ROLES_PATH)
    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    required_columns = {"job title", "required skills"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Kolom CSV tidak lengkap: " +
            ", ".join(sorted(missing_columns))
        )

    df = df.fillna("")
    _job_roles_df = df

    logger.info(
        "Data referensi pekerjaan dimuat: %s baris.",
        len(df)
    )

    return _job_roles_df


def _load_skills_database():
    global _skills_database

    if _skills_database is not None:
        return _skills_database

    if not SKILLS_DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database skill tidak ditemukan: {SKILLS_DB_PATH}"
        )

    with open(SKILLS_DB_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Database skill harus berupa objek JSON.")

    _skills_database = data
    return _skills_database


def extract_skills_from_text(
    text: str,
    skills_db: Dict
) -> List[str]:
    normalized_text = normalize_text(text)
    found = set()

    for skills in skills_db.values():
        if not isinstance(skills, list):
            continue

        for skill in skills:
            normalized_skill = normalize_text(skill)

            if not normalized_skill:
                continue

            pattern = (
                r"(?<!\w)" +
                re.escape(normalized_skill) +
                r"(?!\w)"
            )

            if re.search(pattern, normalized_text):
                found.add(normalized_skill)

    return sorted(found)


def parse_required_skills(value: Any) -> List[str]:
    """Mendukung format CSV dipisah |, list, atau JSON list."""
    if value is None:
        return []

    if isinstance(value, list):
        raw_skills = value

    elif isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        if value.startswith("["):
            try:
                parsed = json.loads(value)
                raw_skills = (
                    parsed if isinstance(parsed, list) else []
                )
            except json.JSONDecodeError:
                return []
        else:
            raw_skills = value.split("|")

    else:
        return []

    result = []
    seen = set()

    for skill in raw_skills:
        normalized = normalize_text(skill)

        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)

    return result


def calculate_skill_match_percentage(
    cv_skills: List[str],
    required_skills: List[str]
) -> float:
    """
    Skor 0 merupakan fallback numerik saat requirements kosong.
    Periksa skill_match_available sebelum menafsirkan skor.
    """
    required = set(parse_required_skills(required_skills))

    if not required:
        return 0.0

    available = set(parse_required_skills(cv_skills))
    matched = len(available & required)

    return round(100.0 * matched / len(required), 2)


def get_skill_gap(
    cv_skills: List[str],
    required_skills: List[str]
) -> List[str]:
    available = set(parse_required_skills(cv_skills))
    required = set(parse_required_skills(required_skills))

    return sorted(required - available)


def predict_career_categories(
    cv_text: str,
    top_k: int = 3
) -> Dict[str, Any]:
    if not isinstance(cv_text, str) or not cv_text.strip():
        return {
            "status": "error",
            "error": "CV text tidak boleh kosong.",
            "predicted_categories": [],
            "predictions": [],
            "probabilities": {}
        }

    try:
        classifier, vectorizer = _load_model()

        features = vectorizer.transform(
            [normalize_text(cv_text)]
        )

        probabilities = classifier.predict_proba(features)[0]
        classes = classifier.classes_

        top_k = max(1, min(int(top_k), len(classes)))

        indices = np.argsort(probabilities)[::-1][:top_k]

        categories = [
            str(classes[index])
            for index in indices
        ]

        probability_map = {
            str(classes[index]): float(probabilities[index])
            for index in indices
        }

        return {
            "status": "success",
            "predicted_categories": categories,
            "predictions": categories,
            "probabilities": probability_map,
            "top_category": categories[0]
        }

    except Exception:
        logger.exception(
            "Gagal memprediksi kategori karier Feature 2."
        )

        return {
            "status": "error",
            "error": "Prediksi kategori karier gagal.",
            "predicted_categories": [],
            "predictions": [],
            "probabilities": {}
        }


def _role_similarity(
    predicted_title: str,
    csv_title: str
) -> float:
    predicted = normalize_role_title(predicted_title)
    candidate = normalize_role_title(csv_title)

    if not predicted or not candidate:
        return 0.0

    if predicted == candidate:
        return 1.0

    predicted_tokens = set(predicted.split())
    candidate_tokens = set(candidate.split())

    predicted_specific = (
        predicted_tokens - GENERIC_ROLE_WORDS
    )
    candidate_specific = (
        candidate_tokens - GENERIC_ROLE_WORDS
    )

    shared_specific = predicted_specific & candidate_specific

    # Hindari mencocokkan Backend dan Frontend hanya
    # karena keduanya sama-sama memiliki kata Developer.
    if (
        predicted_specific and candidate_specific
        and not shared_specific
    ):
        return 0.0

    if shared_specific:
        coverage = (
            len(shared_specific) /
            max(len(predicted_specific), 1)
        )
        string_similarity = SequenceMatcher(
            None, predicted, candidate
        ).ratio()

        return 0.75 * coverage + 0.25 * string_similarity

    # Fallback untuk judul yang hanya berisi kata umum.
    return 0.4 * SequenceMatcher(
        None, predicted, candidate
    ).ratio()


def find_matching_roles(
    predicted_category: str,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """Cari judul pekerjaan yang relevan dengan label model."""
    roles_df = _load_job_roles()

    candidates = []

    for _, row in roles_df.iterrows():
        title = str(row.get("job title", "")).strip()

        if not title:
            continue

        similarity = _role_similarity(
            predicted_category, title
        )

        if similarity < 0.55:
            continue

        role = {
            "job title": title,
            "category": str(row.get("category", "")),
            "required_skills": parse_required_skills(
                row.get("required skills", "")
            ),
            "salary range": str(
                row.get("salary range", "")
            ),
            "education requirement": str(
                row.get("education requirement", "")
            ),
            "experience years": row.get(
                "experience years", ""
            ),
            "_title_similarity": similarity
        }

        candidates.append(role)

    candidates.sort(
        key=lambda item: item["_title_similarity"],
        reverse=True
    )

    return candidates[:max(0, int(top_n))]


def _build_learning_path(
    recommendations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    learning_path = []

    for recommendation in recommendations:
        missing = recommendation["missing_skills"]

        learning_path.append({
            "rank": recommendation["rank"],
            "role_title": recommendation["role_title"],
            "suggested_skills": missing,
            "steps": [
                {
                    "step": index,
                    "skill": skill,
                    "activity": (
                        f"Pelajari dasar {skill}, "
                        "lalu buat latihan atau proyek kecil."
                    )
                }
                for index, skill in enumerate(missing, 1)
            ]
        })

    return learning_path


def recommend_career(cv_text: str) -> Dict[str, Any]:
    valid, message = validate_cv_text(cv_text)

    if not valid:
        return {
            "status": "error",
            "error": message
        }

    try:
        skills_db = _load_skills_database()

        detected_skills = extract_skills_from_text(
            cv_text, skills_db
        )

        prediction = predict_career_categories(
            cv_text, top_k=3
        )

        if prediction["status"] != "success":
            return prediction

        categories = prediction["predicted_categories"]
        probabilities = prediction["probabilities"]

        recommendations = []
        skill_gaps = {}
        used_job_titles = set()

        # Satu rekomendasi untuk setiap kategori Top-3 model.
        for rank, predicted_category in enumerate(
            categories, start=1
        ):
            matched_roles = find_matching_roles(
                predicted_category, top_n=20
            )

            selected_role = None

            for candidate in matched_roles:
                key = normalize_role_title(
                    candidate["job title"]
                )

                if key not in used_job_titles:
                    selected_role = candidate
                    used_job_titles.add(key)
                    break

            if selected_role:
                role_title = selected_role["job title"]
                category = selected_role["category"]
                required_skills = selected_role[
                    "required_skills"
                ]
                salary_range = selected_role[
                    "salary range"
                ]
                source = "job_roles_csv"
            else:
                # Tetap tampilkan label yang benar-benar
                # diprediksi model, tanpa menciptakan
                # persyaratan pekerjaan yang tidak diketahui.
                role_title = predicted_category
                category = predicted_category
                required_skills = []
                salary_range = ""
                source = "classifier_label"

            skill_match_available = bool(required_skills)

            match_percentage = (
                calculate_skill_match_percentage(
                    detected_skills, required_skills
                )
            )

            missing_skills = get_skill_gap(
                detected_skills, required_skills
            )

            recommendations.append({
                "rank": rank,
                "role_title": role_title,
                "category": category,
                "predicted_category": predicted_category,
                "category_probability": probabilities.get(
                    predicted_category, 0.0
                ),
                "match_percentage": match_percentage,
                "skill_match_available": skill_match_available,
                "required_skills": required_skills,
                "missing_skills": missing_skills,
                "salary_range": salary_range,
                "source": source
            })

            skill_gaps[role_title] = missing_skills

        profile_summary = {
            "cv_length": len(cv_text),
            "detected_skills_count": len(detected_skills),
            "top_category": categories[0],
            "all_predicted_categories": categories,
            "category_probabilities": probabilities,
            "skill_match_note": (
                "Persentase skill matching berbeda dari "
                "probabilitas kategori classifier. "
                "Jika skill_match_available=False, "
                "persyaratan skill belum diketahui."
            )
        }

        return {
            "status": "success",
            "predicted_category": categories[0],
            "all_predicted_categories": categories,
            "top_recommendations": recommendations,
            "detected_skills": detected_skills,
            "skill_gaps": skill_gaps,
            "learning_path": _build_learning_path(
                recommendations
            ),
            "profile_summary": profile_summary
        }

    except Exception:
        logger.exception(
            "Gagal menghasilkan rekomendasi karier."
        )
        return {
            "status": "error",
            "error": "Proses rekomendasi karier gagal."
        }


def validate_cv_text(
    cv_text: str,
    min_length: int = 50
) -> Tuple[bool, str]:
    if not isinstance(cv_text, str):
        return False, "CV text harus berupa string."

    if not cv_text.strip():
        return False, "CV text tidak boleh kosong."

    if len(cv_text.strip()) < min_length:
        return (
            False,
            f"CV text terlalu pendek (minimal {min_length} karakter)."
        )

    return True, "OK"


def reset_cache():
    global _classifier, _vectorizer
    global _job_roles_df, _skills_database

    _classifier = None
    _vectorizer = None
    _job_roles_df = None
    _skills_database = None
