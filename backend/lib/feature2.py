
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
import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd

from .cv_understanding import canonical_skill, understand_cv

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

# Explicit, reviewed aliases to titles that actually exist in job_roles.csv.
# A missing/ambiguous equivalent is intentionally unknown, never a fuzzy guess.
CATEGORY_ROLE_ALIASES = {
    "AI Engineer": ("AI/ML Specialist",),
    "Blockchain": ("Blockchain Developer",),
    "Data Science": ("Data Scientist",),
    "DevOps": ("DevOps Engineer",),
    "DotNet Developer": ("C# Developer",),
    "Java Developer": ("Java Backend Developer",),
    "Mobile Developer": ("Mobile Developer Android", "Mobile Developer iOS"),
    "Software Developer": ("Software Engineer",),
    "System Administrator": ("Systems Administrator",),
    "Testing": ("Software Test Engineer",),
    "UI/UX Designer": ("UX Designer", "UI Designer"),
    "Web Designing": ("Web Designer",),
}
SKILL_ALIASES = {"rest apis": "rest api", "restful apis": "rest api"}


def normalize_skill(skill):
    canonical = canonical_skill(skill)
    return SKILL_ALIASES.get(canonical, canonical)


def normalize_text(text: str) -> str:
    if text is None:
        return ""

    text = unicodedata.normalize("NFKC", str(text))
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def normalize_role_title(title: str) -> str:
    # No synonym expansion here: role identity must not erase specialization.
    return re.sub(r"\s+", " ", normalize_text(title)).strip()


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
    return sorted({normalize_skill(skill["name"]) for skill in understand_cv(text, skills_db)["skills"]})


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
        normalized = normalize_skill(skill) if isinstance(skill, str) else ""

        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)

    return result


def calculate_skill_match_percentage(
    cv_skills: List[str],
    required_skills: List[str]
) -> float | None:
    """Evidence coverage, distinct from classifier probability. Empty requirements are unknown."""
    required = set(parse_required_skills(required_skills))

    if not required:
        return None

    available = set(parse_required_skills(cv_skills))
    matched = len(_matched_skills(available, required))

    return round(100.0 * matched / len(required), 2)


def get_skill_gap(
    cv_skills: List[str],
    required_skills: List[str]
) -> List[str] | None:
    available = set(parse_required_skills(cv_skills))
    required = set(parse_required_skills(required_skills))

    return sorted(required - set(_matched_skills(available, required))) if required else None


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

    except Exception as exc:
        logger.error(
            "Gagal memprediksi kategori karier Feature 2 | error_type=%s", type(exc).__name__
        )

        return {
            "status": "error",
            "error": "Prediksi kategori karier gagal.",
            "predicted_categories": [],
            "predictions": [],
            "probabilities": {}
        }


def _matched_skills(available, required):
    available = set(available)
    if "html/css" in available:
        available.update({"html", "css"})
    matched = set(available) & set(required)
    # A bundled HTML/CSS requirement is supported when BOTH components have evidence.
    if "html/css" in required and {"html", "css"}.issubset(available):
        matched.add("html/css")
    return sorted(matched)


def salary_metadata(raw_value="", reference=None):
    """The local reference has no verified currency, period or labour market."""
    return {
        "status": "unknown", "currency": None, "payment_period": None,
        "location": None, "market": None, "raw_reference_range": raw_value or None,
        "source": reference, "note": "Reference range lacks currency, payment period and market; not a verified salary estimate.",
    }


def find_matching_roles(predicted_category: str, top_n: int = 3) -> List[Dict[str, Any]]:
    roles_df = _load_job_roles()
    targets = CATEGORY_ROLE_ALIASES.get(predicted_category, (predicted_category,))
    order = {normalize_role_title(title): index for index, title in enumerate(targets)}
    candidates = []
    for index, row in roles_df.iterrows():
        title = str(row.get("job title", "")).strip()
        if normalize_role_title(title) not in order:
            continue
        candidates.append({
            "job title": title,
            "category": str(row.get("category", "")),
            "required_skills": parse_required_skills(row.get("required skills", "")),
            "salary range": str(row.get("salary range", "")),
            "reference_row": int(index) + 2,
            "required_skills_original": str(row.get("required skills", "")),
            "mapping_method": "explicit_alias" if predicted_category in CATEGORY_ROLE_ALIASES else "exact_title",
        })
    candidates.sort(key=lambda role: (order[normalize_role_title(role["job title"])], role["reference_row"]))
    return candidates[:max(0, int(top_n))]


def _evidence_profile(cv_text):
    # This is a skill-evidence lexicon, NOT the trained TF-IDF vocabulary.
    vocabulary = dict(_load_skills_database())
    reference_skills = []
    reference_families = set()
    classifier, _ = _load_model()
    if len(classifier.classes_) != 30:
        raise ValueError("Feature 2 requires the existing 30-category classifier.")
    for category in classifier.classes_:
        for role in find_matching_roles(str(category), top_n=20):
            reference_skills.extend(role["required_skills"])
            if role["category"]:
                reference_families.add(role["category"])
    # Recognize explicit skills from adjacent IT/data/design reference roles too
    # (e.g. Tableau/Power BI), without assigning those roles to a classifier label.
    for _, row in _load_job_roles().iterrows():
        if row.get("category", "") in reference_families:
            reference_skills.extend(parse_required_skills(row.get("required skills", "")))
    vocabulary["feature2_reference_skills"] = sorted(set(reference_skills))
    vocabulary["feature2_literal_variants"] = list(SKILL_ALIASES)
    profile = understand_cv(cv_text, vocabulary)
    # Consolidate positive variants while retaining their independent evidence.
    skills = {}
    for item in profile["skills"]:
        name = normalize_skill(item["name"])
        record = {**item, "name": name, "evidence_items": [
            {**mention, "name": name} for mention in item["evidence_items"]
        ]}
        if name in skills:
            skills[name]["evidence_items"].extend(record["evidence_items"])
        else:
            skills[name] = record
    if any(len(item["evidence_items"]) > 5 for item in skills.values()):
        profile["quality_warnings"].append("Alias evidence consolidated with a limit of 5 positive excerpts per canonical skill.")
        for item in skills.values():
            item["evidence_items"] = item["evidence_items"][:5]
    profile["skills"] = [skills[name] for name in sorted(skills)]
    profile["excluded_skill_mentions"] = [
        {**item, "name": normalize_skill(item["name"])} for item in profile["excluded_skill_mentions"]
    ]
    profile["skill_vocabulary_source"] = "base skills_database + CSV terms in reference families covered by validated mappings; TF-IDF vocabulary unchanged"
    return profile


def _build_learning_path(
    recommendations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    learning_path = []
    for recommendation in recommendations:
        missing = recommendation["missing_skills"]
        available = recommendation["skill_match_available"]
        learning_path.append({
            "rank": recommendation["rank"], "role_title": recommendation["role_title"],
            "status": "unknown_requirements" if not available else ("evidence_gap" if missing else "covered_by_evidence"),
            "suggested_skills": missing or [],
            "note": "Belum terdeteksi bukan bukti tidak memiliki skill; verifikasi kebutuhan role dan bukti CV.",
            "steps": [{
                "step": index, "skill": skill,
                "activity": f"Jika sudah menguasai {skill}, tambahkan bukti penggunaannya di CV; jika belum, pelajari dasar dan buat latihan/proyek kecil.",
            } for index, skill in enumerate(missing or [], 1)],
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
        profile = _evidence_profile(cv_text)
        detected_skills = [item["name"] for item in profile["skills"]]

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

            candidates = [role for role in matched_roles if normalize_role_title(role["job title"]) not in used_job_titles]
            # Evidence may select a representative WITHIN the same predicted category;
            # it never reorders categories or alters their probabilities.
            candidates.sort(key=lambda role: (
                -len(_matched_skills(detected_skills, role["required_skills"])),
                -(calculate_skill_match_percentage(detected_skills, role["required_skills"]) or 0),
                role["reference_row"],
            ))
            selected_role = candidates[0] if candidates else None
            specialization_evidence = {}
            if len(candidates) > 1:
                common = set.intersection(*(set(role["required_skills"]) for role in candidates))
                specialization_evidence = {role["job title"]: _matched_skills(detected_skills, set(role["required_skills"]) - common) for role in candidates}
                candidates.sort(key=lambda role: (
                    -len(_matched_skills(detected_skills, set(role["required_skills"]) - common)),
                    -len(_matched_skills(detected_skills, role["required_skills"])), role["reference_row"],
                ))
                selected_role = candidates[0]
                best_evidence = len(_matched_skills(detected_skills, set(selected_role["required_skills"]) - common))
                tied = sum(len(_matched_skills(detected_skills, set(role["required_skills"]) - common)) == best_evidence for role in candidates)
                if not best_evidence or tied != 1:
                    selected_role = None  # No distinct evidence winner: never resolve specialization by CSV row order.
            if selected_role:
                used_job_titles.add(normalize_role_title(selected_role["job title"]))

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

            reference = {
                "dataset": "data/raw/job_roles.csv", "row": selected_role["reference_row"],
                "role_title": selected_role["job title"],
                "required_skills_original": selected_role["required_skills_original"],
                "sha256": hashlib.sha256(JOB_ROLES_PATH.read_bytes()).hexdigest(),
                "scope": "local role reference; not requirements of a specific employer",
            } if selected_role else None
            salary = salary_metadata(salary_range, reference)
            matched_evidence = {}
            for skill in _matched_skills(detected_skills, required_skills):
                evidence_names = {skill}
                if skill == "html/css":
                    evidence_names.update({"html", "css"})
                if skill in {"html", "css"}:
                    evidence_names.add("html/css")
                matched_evidence[skill] = [item for item in profile["skills"] if item["name"] in evidence_names]

            recommendations.append({
                "rank": rank,
                "role_title": role_title,
                "category": category,
                "predicted_category": predicted_category,
                "category_probability": probabilities[predicted_category],
                "match_percentage": match_percentage,
                "skill_match_available": skill_match_available,
                "required_skills": required_skills,
                "missing_skills": missing_skills,
                "salary_range": "",  # Frontend must not show an unverified numeric salary.
                "salary_metadata": salary,
                "requirements_status": "known" if skill_match_available else "unknown",
                "requirements_scope": "reference_role" if skill_match_available else "unknown",
                "specialization_status": ("evidence_supported" if len(matched_roles) > 1 else "category_reference") if selected_role else "unknown",
                "skill_evidence": matched_evidence if skill_match_available else None,
                "source": source,
                "skill_match_status": "known" if skill_match_available else "unknown",
                "matched_skills": _matched_skills(detected_skills, required_skills) if skill_match_available else None,
                "skill_match_note": (
                    "Cakupan requirements yang didukung bukti CV; 0% bukan bukti kandidat tidak mampu."
                    if skill_match_available else "Requirements role belum dapat dipastikan dari referensi; persentase dan gap unknown."
                ),
                "mapping_status": "mapped" if selected_role else ("ambiguous_specialization" if matched_roles else "unknown_reference"),
                "mapping_scope": "representative_reference" if selected_role else "classifier_category_only",
                "specialization_evidence": specialization_evidence,
                "mapping_method": selected_role["mapping_method"] if selected_role else None,
                "reference": reference,
            })

            used_job_titles.add(normalize_role_title(role_title))
            skill_gaps[role_title] = missing_skills

        profile_summary = {
            "schema_version": "ai3d.1",
            "cv_understanding": profile,
            "role_recommendations": recommendations,
            "skill_gaps": skill_gaps,
            "model": {"classifier": "LogisticRegression", "vectorizer": "TfidfVectorizer", "classes": 30,
                      "artifact_sha256": hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()},
            "reference_sha256": hashlib.sha256(JOB_ROLES_PATH.read_bytes()).hexdigest(),
            "ranking_policy": "Top 3 raw classifier probabilities; skill coverage never reranks categories",
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

    except Exception as exc:
        logger.error(
            "Gagal menghasilkan rekomendasi karier | error_type=%s", type(exc).__name__
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
