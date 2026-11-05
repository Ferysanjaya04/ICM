"""ICM — Feature 1: CV vs Job Requirement Matching.

Kontrak publik dipertahankan agar kompatibel dengan analysis.services.AnalysisService:
    analyze_cv_job(cv_text, job_text, cv_filename=None,
                   skills_db_path=None, model_manager=None) -> dict

Pipeline: validasi -> skill matching -> pengalaman -> pendidikan ->
semantic similarity -> compatibility scoring -> rekomendasi.

Catatan: compatibility score adalah heuristik kesesuaian CV terhadap lowongan,
BUKAN peluang diterima bekerja atau probabilitas statistik.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    cosine_similarity = None
    HAS_SKLEARN = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

WEIGHT_SEMANTIC = 0.25
WEIGHT_SKILL = 0.40
WEIGHT_EXPERIENCE = 0.20
WEIGHT_EDUCATION = 0.15
COMPATIBILITY_HIGH_THRESHOLD = 80
COMPATIBILITY_MEDIUM_THRESHOLD = 60
MODEL_NAME = "all-MiniLM-L6-v2"

MONTHS = {
    "januari": 1, "january": 1, "jan": 1,
    "februari": 2, "february": 2, "feb": 2,
    "maret": 3, "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "june": 6, "jun": 6,
    "juli": 7, "july": 7, "jul": 7,
    "agustus": 8, "august": 8, "agu": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "oktober": 10, "october": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "december": 12, "des": 12, "dec": 12,
}
MONTH_PATTERN = "|".join(sorted(map(re.escape, MONTHS), key=len, reverse=True))
CURRENT_PATTERN = r"present|current|ongoing|now|sekarang|saat\s+ini|hingga\s+kini"

# Compatible with date spans like "Jan 2022 - Mar 2024", "2021 – 2023",
# "2024 - Present", "Mei 2025 sampai sekarang".
PERIOD_PATTERN = re.compile(
    rf"(?<!\w)(?:(?P<start_month>{MONTH_PATTERN})\.?\s+)?"
    rf"(?P<start_year>(?:19|20)\d{{2}})\s*"
    rf"(?:[-–—]|\bsampai\b|\bto\b|\bhingga\b)\s*"
    rf"(?:(?:(?P<end_month>{MONTH_PATTERN})\.?\s+)?"
    rf"(?P<end_year>(?:19|20)\d{{2}})|(?P<current>{CURRENT_PATTERN}))(?!\w)",
    re.IGNORECASE,
)
# Backward-compatible exported regex constants.
DATE_RANGE_PATTERN = PERIOD_PATTERN
YEAR_RANGE_PATTERN = re.compile(
    rf"\b(?:19|20)\d{{2}}\s*[-–—]\s*(?:(?:19|20)\d{{2}}|(?:{CURRENT_PATTERN}))\b",
    re.IGNORECASE,
)

SKILL_ALIASES = {
    "js": "javascript", "javascript": "javascript",
    "reactjs": "react", "react.js": "react", "react js": "react", "react": "react",
    "nodejs": "node.js", "node js": "node.js", "node.js": "node.js",
    "postgres": "postgresql", "postgresql": "postgresql",
    "restful api": "rest api", "rest api": "rest api",
    "ts": "typescript", "typescript": "typescript",
    "k8s": "kubernetes", "kubernetes": "kubernetes",
    "amazon web services": "aws", "aws": "aws",
    "google cloud": "gcp", "google cloud platform": "gcp", "gcp": "gcp",
    "agile methodology": "agile", "agile": "agile",
    "scrum framework": "scrum", "scrum": "scrum",
    "mysql": "mysql", "nosql": "nosql",
}

FRESH_GRADUATE_PHRASES = (
    "fresh graduate", "fresh graduates", "freshgraduate", "freshgraduates",
    "fresh-graduate", "lulusan baru", "new graduate", "new graduates",
    "recent graduate", "recent graduates",
)
PORTFOLIO_PHRASES = ("portfolio", "portofolio", "project portfolio", "proyek nyata")

# General headings and context words, NOT names of particular CVs/institutions.
HEADING_RE = re.compile(
    r"^(?P<heading>(?:professional\s+)?(?:work\s+)?experience|"
    r"employment(?:\s+history)?|work\s+history|career\s+history|"
    r"pengalaman(?:\s+kerja|\s+profesional)?|riwayat\s+pekerjaan|"
    r"internship(?:s)?|magang|praktik\s+kerja(?:\s+lapangan)?|"
    r"projects?|personal\s+projects?|proyek|projek|portofolio|portfolio|"
    r"education|academic\s+background|pendidikan|riwayat\s+pendidikan|"
    r"certifications?|sertifikasi|skills?|keahlian|kompetensi|"
    r"summary|profile|profil|ringkasan|contact|kontak)\s*:?[\s]*$",
    re.IGNORECASE,
)
WORK_TERMS = re.compile(
    r"\b(?:engineer|developer|programmer|analyst|administrator|technician|"
    r"specialist|consultant|designer|scientist|architect|manager|lead|"
    r"tester|qa|devops|freelanc(?:e|er)|karyawan|pegawai|staff|staf|"
    r"bekerja|employment|full[- ]?time|part[- ]?time)\b",
    re.IGNORECASE,
)
INTERNSHIP_TERMS = re.compile(r"\b(?:intern(?:ship)?|magang|pkl)\b", re.IGNORECASE)
PROJECT_TERMS = re.compile(r"\b(?:project|proyek|projek|portfolio|portofolio)\b", re.IGNORECASE)
EDUCATION_TERMS = re.compile(
    r"\b(?:university|universitas|politeknik|institute|institut|college|"
    r"sekolah|academy|akademi|bachelor|sarjana|master|magister|diploma|"
    r"phd|doktor|education|pendidikan|s1|s2|s3|d3|d4)\b",
    re.IGNORECASE,
)

TECHNOLOGY_FIELDS = {
    "computer science", "computer engineering", "information technology",
    "information systems", "software engineering", "rekayasa perangkat lunak",
    "teknik informatika", "informatika", "sistem informasi", "ilmu komputer",
    "teknik komputer", "teknologi informasi", "teknologi rekayasa internet",
    "data science", "cybersecurity", "cyber security", "electrical engineering",
    "electronics engineering",
}
NONTECH_FIELDS = {
    "business", "business administration", "management", "manajemen", "marketing",
    "design", "finance", "accounting", "akuntansi", "mathematics", "statistika",
    "statistics", "physics", "biology", "chemistry", "hukum", "law",
}
ALL_FIELDS = sorted(TECHNOLOGY_FIELDS | NONTECH_FIELDS, key=len, reverse=True)


def normalize_text(text: str) -> str:
    """Normalize case/whitespace without destroying e.g. C++, C#, Node.js."""
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def load_skills_database(db_path: Optional[str] = None) -> Dict[str, List[str]]:
    """Load skills_database.json; support the existing category -> skills schema."""
    path = Path(db_path) if db_path is not None else Path(__file__).resolve().parent / "skills_database.json"
    if not path.is_file():
        raise FileNotFoundError(f"Skills database tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Skills database harus berupa object JSON kategori -> list keterampilan")
    if not any(isinstance(items, list) and items for items in data.values()):
        raise ValueError("Skills database tidak mempunyai daftar keterampilan yang dapat digunakan")
    return data


def normalize_skill(skill: str) -> str:
    normalized = normalize_text(skill)
    return SKILL_ALIASES.get(normalized, normalized)


def extract_skills(text: str, skills_database: Dict[str, List[str]]) -> List[str]:
    """Match known skills and aliases using boundaries (no naive substring)."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    # Canonical skill -> possible normalized spellings.
    vocabulary: Dict[str, set[str]] = {}
    for items in skills_database.values():
        if not isinstance(items, list):
            continue
        for skill in items:
            if not isinstance(skill, str) or not skill.strip():
                continue
            canonical = normalize_skill(skill)
            vocabulary.setdefault(canonical, set()).add(normalize_text(skill))
            vocabulary[canonical].add(canonical)

    # Only allow aliases whose canonical target is actually in the reference DB.
    for alias, canonical in SKILL_ALIASES.items():
        if canonical in vocabulary:
            vocabulary[canonical].add(normalize_text(alias))

    detected = set()
    for canonical, variants in vocabulary.items():
        for variant in sorted(variants, key=len, reverse=True):
            if re.search(rf"(?<!\w){re.escape(variant)}(?!\w)", normalized):
                detected.add(canonical)
                break
    return sorted(detected)


def extract_explicit_experience_years(text: str, prefer_min: bool = False) -> Optional[float]:
    """Read stated experience years; min for job requirements, max for CV."""
    normalized = normalize_text(text)
    patterns = (
        r"\b(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b",
        r"\b(?:professional\s+|work\s+)?experience\s*[:\-]\s*(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        r"\b(\d+(?:[.,]\d+)?)\s*\+?\s*tahun\s+(?:pengalaman|bekerja|kerja)\b",
        r"\b(?:pengalaman(?:\s+kerja)?|minimal|minimal pengalaman)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*\+?\s*tahun\b",
        r"\b(?:minimum|at least|minimal|min\.)\s*(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?|tahun)\b",
    )
    values: List[float] = []
    for pattern in patterns:
        for raw in re.findall(pattern, normalized):
            value = float(raw.replace(",", "."))
            if 0 <= value <= 60:
                values.append(value)
    # "2-5 years experience": job needs >=2; CV must NOT claim 5 years.
    range_pattern = r"\b(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:years?|yrs?|tahun)(?:\s+(?:of\s+)?(?:experience|pengalaman))?\b"
    for low, high in re.findall(range_pattern, normalized):
        low_n, high_n = float(low.replace(",", ".")), float(high.replace(",", "."))
        if 0 <= low_n <= high_n <= 60:
            if prefer_min:
                values.append(low_n)
    if not values:
        return None
    return min(values) if prefer_min else max(values)


def detect_career_status(text: str) -> Dict[str, bool]:
    normalized = normalize_text(text)
    return {
        "fresh_graduate": any(p in normalized for p in FRESH_GRADUATE_PHRASES),
        "internship": bool(INTERNSHIP_TERMS.search(normalized)),
        "project_experience": bool(PROJECT_TERMS.search(normalized)),
    }


def calculate_duration_months(start_year: int, start_month: int,
                              end_year: int, end_month: int) -> Optional[int]:
    if any(x is None for x in (start_year, start_month, end_year, end_month)):
        return None
    if not 1 <= start_month <= 12 or not 1 <= end_month <= 12:
        return None
    start = start_year * 12 + start_month - 1
    end_exclusive = end_year * 12 + end_month
    return end_exclusive - start if end_exclusive > start else None


def parse_period(period: Optional[str]) -> Dict[str, Optional[Any]]:
    """Parse an actual date span. Year-only duration is conservative estimate."""
    empty = dict(start_year=None, start_month=None, end_year=None,
                 end_month=None, duration_months=None)
    if not period or not isinstance(period, str):
        return empty
    match = PERIOD_PATTERN.search(period)
    if not match:
        return empty
    start_year = int(match.group("start_year"))
    start_month = MONTHS.get(match.group("start_month").lower()) if match.group("start_month") else None
    today = date.today()
    if match.group("current"):
        end_year, end_month = today.year, today.month
    else:
        end_year = int(match.group("end_year"))
        end_month = MONTHS.get(match.group("end_month").lower()) if match.group("end_month") else None
    if start_year > today.year or end_year > today.year or end_year < start_year:
        return empty
    if start_month is not None and end_month is not None:
        duration = calculate_duration_months(start_year, start_month, end_year, end_month)
    else:
        # Only years are known. Avoid assuming Jan-Dec for both endpoints.
        duration = max(0, (end_year - start_year) * 12)
    if duration is None:
        return empty
    return dict(start_year=start_year, start_month=start_month,
                end_year=end_year, end_month=end_month, duration_months=duration)


def _section_for_heading(line: str) -> Optional[str]:
    match = HEADING_RE.match(line.strip())
    if not match:
        return None
    heading = normalize_text(match.group("heading"))
    if any(w in heading for w in ("education", "academic", "pendidikan")):
        return "education"
    if any(w in heading for w in ("intern", "magang", "praktik")):
        return "internship"
    if any(w in heading for w in ("project", "proyek", "projek", "portfolio", "portofolio")):
        return "project"
    if any(w in heading for w in ("experience", "work", "employment", "career", "pengalaman", "pekerjaan")):
        return "work"
    return "other"


def _classify_entry(section: Optional[str], context: str) -> str:
    # Local positive evidence overrides an unrelated section heading.
    if INTERNSHIP_TERMS.search(context):
        return "internship"
    if section in ("work", "internship", "education", "project"):
        return section
    if EDUCATION_TERMS.search(context):
        return "education"
    if PROJECT_TERMS.search(context):
        return "project"
    if WORK_TERMS.search(context):
        return "work"
    return "unknown"


def extract_entry_periods(text: str) -> List[Dict[str, Any]]:
    """Identify dated entries in arbitrary CVs, without hardcoded person/company names.

    Only entries positively classified as work or internship contribute to
    estimated professional experience. Education and projects stay separate.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section: Optional[str] = None
    results: List[Dict[str, Any]] = []
    for index, line in enumerate(lines):
        new_section = _section_for_heading(line)
        if new_section is not None:
            section = new_section
            continue
        for match in PERIOD_PATTERN.finditer(line):
            period = match.group(0)
            parsed = parse_period(period)
            if parsed["duration_months"] is None:
                continue
            # Title may be on this line, or immediately above a line of dates.
            remainder = (line[:match.start()] + " " + line[match.end():]).strip(" -–—|:,")
            preceding = lines[index - 1] if index else ""
            succeeding = lines[index + 1] if index + 1 < len(lines) else ""
            title = remainder or preceding or succeeding or "Unspecified entry"
            # Don't accidentally classify from a distant CV paragraph.
            context = " ".join((title, preceding if remainder else ""))
            category = _classify_entry(section, context)
            results.append({
                "title": title[:200], "category": category, "period": period,
                **parsed,
                "precision": "month" if match.group("start_month") and
                (match.group("end_month") or match.group("current")) else "year_estimate",
            })
    return results


def _unique_work_months(entries: List[Dict[str, Any]]) -> int:
    """Union of inferred work/internship months; overlapping jobs not double-counted."""
    month_ids = set()
    for entry in entries:
        if entry["category"] not in ("work", "internship"):
            continue
        months = entry.get("duration_months")
        if not isinstance(months, int) or months <= 0:
            continue
        sy, ey = entry["start_year"], entry["end_year"]
        sm, em = entry["start_month"], entry["end_month"]
        start = sy * 12 + (sm - 1 if sm else 0)
        # Coarse start-year without a month -> conservative year-only bound.
        # Do not inflate the estimate by using an exact end-month in this case.
        end_exclusive = ey * 12 + (em if (sm is not None and em is not None) else 0)
        if end_exclusive <= start:
            continue
        month_ids.update(range(start, end_exclusive))
    return len(month_ids)


def _education_context(text: str) -> str:
    """Prefer education lines/sections over irrelevant job titles or skill lists."""
    if not isinstance(text, str):
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    relevant: List[str] = []
    section: Optional[str] = None
    for line in lines:
        heading = _section_for_heading(line)
        if heading is not None:
            section = heading
            continue
        if section == "education" or re.search(
            r"\b(?:degree|gelar|sarjana|bachelor|master|magister|phd|doktor|diploma|s1|s2|s3|d3|d4)\b",
            line, re.IGNORECASE,
        ):
            relevant.append(line)
    return " ".join(relevant) if relevant else text


def get_education_level(text: str) -> int:
    """0=unknown, 1=diploma, 2=bachelor/D4, 3=master, 4=PhD."""
    normalized = normalize_text(_education_context(text))
    level_patterns = [
        (4, r"\b(?:ph\.?d\.?|doctorate|doktor|s3)\b"),
        (3, r"\b(?:masters?|m\.?sc\.?|magister|s2)\b"),
        (2, r"\b(?:bachelors?|b\.?sc\.?|sarjana(?:\s+terapan)?|s1|d4)\b"),
        (1, r"\b(?:diploma|associate(?:\s+degree)?|d3|d2|d1)\b"),
    ]
    for level, pattern in level_patterns:
        if re.search(pattern, normalized):
            return level
    return 0


def get_education_field(text: str) -> Optional[str]:
    normalized = normalize_text(_education_context(text))
    for field in ALL_FIELDS:
        if re.search(rf"(?<!\w){re.escape(field)}(?!\w)", normalized):
            return field
    return None


@lru_cache(maxsize=1)
def _get_default_semantic_model():
    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError("sentence-transformers belum terpasang")
    return SentenceTransformer(MODEL_NAME)


def calculate_semantic_score(cv_text: str, job_text: str, model_manager=None) -> float:
    """Cosine similarity in [0,100]; reuse AnalysisService's model manager."""
    if not HAS_SKLEARN or not HAS_NUMPY:
        raise ImportError("scikit-learn dan numpy diperlukan untuk semantic scoring")
    if not isinstance(cv_text, str) or not cv_text.strip() or not isinstance(job_text, str) or not job_text.strip():
        raise ValueError("CV dan job requirement harus berisi teks")
    model = getattr(model_manager, "model", None) if model_manager is not None else None
    if model is None:
        model = _get_default_semantic_model()
    embeddings = model.encode(
        [cv_text.strip(), job_text.strip()],
        convert_to_numpy=True, normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype=float)
    if embeddings.ndim != 2 or embeddings.shape[0] != 2 or not np.isfinite(embeddings).all():
        raise ValueError("Model menghasilkan embedding yang tidak valid")
    similarity = float(cosine_similarity(embeddings[0:1], embeddings[1:2])[0][0])
    return round(max(0.0, min(1.0, similarity)) * 100, 2)


def calculate_skill_score(matched_skills: List[str], job_skills: List[str]) -> Optional[float]:
    """Return None if required skills cannot be detected, NOT an invented 100%."""
    required = set(job_skills)
    if not required:
        return None
    return round(100 * len(set(matched_skills) & required) / len(required), 2)


def calculate_experience_score(
    cv_experience_years: Optional[float], required_experience_years: Optional[float],
    cv_status: Dict[str, bool], job_accepts_fresh_graduate: bool,
    job_accepts_portfolio: bool,
) -> Tuple[Optional[float], str]:
    if required_experience_years is None:
        return None, "Experience requirement not specified; no score assigned"
    if required_experience_years <= 0:
        return 100.0, "No minimum experience duration required"
    if cv_experience_years is not None:
        if cv_experience_years >= required_experience_years:
            return 100.0, "Meets experience duration requirement"
        return round(max(0.0, 100 * cv_experience_years / required_experience_years), 2), "Below experience duration requirement"
    if job_accepts_fresh_graduate and cv_status.get("fresh_graduate", False):
        return None, "Fresh graduate accepted; experience duration unknown"
    if cv_status.get("internship", False):
        return None, "Internship detected but duration unavailable"
    if cv_status.get("project_experience", False) or job_accepts_portfolio:
        return None, "Project experience detected; professional duration unavailable"
    return None, "Work experience not detected; duration unavailable"


def calculate_education_score(
    cv_level: int, job_level: int, cv_field: Optional[str], job_field: Optional[str],
) -> Tuple[Optional[float], str]:
    if job_level == 0:
        return None, "Education requirement not detected; no score assigned"
    if cv_level == 0:
        return None, "CV education not detected; cannot verify education requirement"
    if cv_level < job_level:
        return 40.0, "Below required education level"
    if cv_field is not None and job_field is not None:
        if cv_field == job_field:
            return 100.0, "Education level and field match"
        if cv_field in TECHNOLOGY_FIELDS and job_field in TECHNOLOGY_FIELDS:
            return 90.0, "Related technology education field"
        return 70.0, "Education level matches, field differs"
    return 70.0, "Education level matches, field not fully detected"


def calculate_compatibility_score(
    semantic_score: Optional[float], skill_score: Optional[float],
    experience_score: Optional[float], education_score: Optional[float],
) -> Tuple[Optional[float], str]:
    scores = {"semantic": semantic_score, "skill": skill_score,
              "experience": experience_score, "education": education_score}
    weights = {"semantic": WEIGHT_SEMANTIC, "skill": WEIGHT_SKILL,
               "experience": WEIGHT_EXPERIENCE, "education": WEIGHT_EDUCATION}
    available = {}
    for name, score in scores.items():
        if score is None:
            continue
        if not isinstance(score, (float, int)) or not 0 <= float(score) <= 100:
            raise ValueError(f"Skor {name} harus berada di antara 0 dan 100")
        available[name] = float(score)
    if not available:
        return None, "UNDETERMINED"
    total_weight = sum(weights[name] for name in available)
    if total_weight <= 0:
        return None, "UNDETERMINED"
    # Decimal + ROUND_HALF_UP avoids float ties such as 83.125 -> 83.12.
    numerator = sum(
        Decimal(str(available[name])) * Decimal(str(weights[name]))
        for name in available
    )
    denominator = sum(Decimal(str(weights[name])) for name in available)
    score = float((numerator / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    level = "HIGH" if score >= COMPATIBILITY_HIGH_THRESHOLD else (
        "MEDIUM" if score >= COMPATIBILITY_MEDIUM_THRESHOLD else "LOW"
    )
    return score, level


def generate_recommendations(
    missing_skills: List[str], experience_status: str,
    education_score: Optional[float], semantic_score: Optional[float],
    required_experience_years: Optional[float],
) -> List[str]:
    recommendations: List[str] = []
    for skill in missing_skills[:5]:
        recommendations.append(
            f"Skill '{skill}' belum terdeteksi dalam CV. Jika dikuasai, tambahkan contoh "
            "penggunaannya pada pengalaman/proyek; jika belum, prioritaskan untuk dipelajari."
        )
    if "Below experience" in experience_status and required_experience_years is not None:
        recommendations.append(
            f"Lowongan meminta sekitar {required_experience_years:g} tahun pengalaman; "
            "cantumkan pengalaman relevan dan periodenya jika tersedia."
        )
    elif "duration unavailable" in experience_status or "duration unknown" in experience_status:
        recommendations.append("Cantumkan tanggal mulai dan selesai pengalaman kerja atau magang agar durasinya dapat dinilai.")
    elif "Work experience not detected" in experience_status:
        recommendations.append("Pengalaman profesional belum dapat diverifikasi dari CV; perjelas posisi, organisasi dan periode.")
    if education_score is not None and education_score < 70:
        recommendations.append("Tinjau kesesuaian jenjang dan bidang pendidikan dengan persyaratan posisi.")
    if semantic_score is not None and semantic_score < 60:
        recommendations.append("Perjelas hubungan antara pengalaman/proyek CV dan tugas pada job requirement.")
    if not recommendations:
        recommendations.append("Tidak ditemukan gap utama pada komponen yang terukur. Periksa juga komponen yang tidak terdeteksi.")
    return recommendations


def analyze_cv_job(
    cv_text: str, job_text: str, cv_filename: Optional[str] = None,
    skills_db_path: Optional[str] = None, model_manager=None,
) -> Dict[str, Any]:
    """Return the legacy result schema used by AnalysisService._process_feature1_result."""
    if not isinstance(cv_text, str) or not cv_text.strip():
        raise ValueError("CV text tidak boleh kosong")
    if not isinstance(job_text, str) or not job_text.strip():
        raise ValueError("Job text tidak boleh kosong")

    cv_text = cv_text.strip()
    job_text = job_text.strip()
    skills_db = load_skills_database(skills_db_path)
    cv_skills = extract_skills(cv_text, skills_db)
    job_skills = extract_skills(job_text, skills_db)
    matched_skills = sorted(set(cv_skills) & set(job_skills))
    missing_skills = sorted(set(job_skills) - set(cv_skills))
    skill_score = calculate_skill_score(matched_skills, job_skills)

    cv_status = detect_career_status(cv_text)
    job_status = detect_career_status(job_text)
    entry_periods = extract_entry_periods(cv_text)
    cv_explicit_years = extract_explicit_experience_years(cv_text)
    duration_months = _unique_work_months(entry_periods)
    estimated_cv_years = round(duration_months / 12, 2) if duration_months else None
    cv_experience_years = cv_explicit_years if cv_explicit_years is not None else estimated_cv_years
    required_years = extract_explicit_experience_years(job_text, prefer_min=True)
    accepts_fresh = any(p in normalize_text(job_text) for p in FRESH_GRADUATE_PHRASES)
    accepts_portfolio = any(p in normalize_text(job_text) for p in PORTFOLIO_PHRASES)
    exp_score, exp_status = calculate_experience_score(
        cv_experience_years, required_years, cv_status, accepts_fresh, accepts_portfolio,
    )

    cv_level, job_level = get_education_level(cv_text), get_education_level(job_text)
    cv_field, job_field = get_education_field(cv_text), get_education_field(job_text)
    edu_score, edu_status = calculate_education_score(cv_level, job_level, cv_field, job_field)
    semantic_score = calculate_semantic_score(cv_text, job_text, model_manager)
    compatibility_score, compatibility_level = calculate_compatibility_score(
        semantic_score, skill_score, exp_score, edu_score,
    )
    recommendations = generate_recommendations(
        missing_skills, exp_status, edu_score, semantic_score, required_years,
    )
    if not job_skills:
        recommendations.append(
            "Skill requirement spesifik tidak terdeteksi pada lowongan; skill score tidak dihitung. "
            "Periksa deskripsi lowongan dan vocabulary keterampilan."
        )

    available = {
        "semantic": semantic_score is not None, "skill": skill_score is not None,
        "experience": exp_score is not None, "education": edu_score is not None,
    }
    # Additional fields are additive; legacy keys remain unchanged.
    return {
        "feature": "cv_vs_job_requirement", "cv_file": cv_filename,
        "job_requirement_source": "text_input",
        "compatibility": {"score": compatibility_score, "level": compatibility_level},
        "scores": {"semantic": semantic_score, "skill": skill_score,
                   "experience": exp_score, "education": edu_score},
        "skills": {"cv": cv_skills, "job_requirement": job_skills,
                   "matched": matched_skills, "missing_or_not_detected": missing_skills},
        "experience": {
            "explicit_cv_years": cv_explicit_years,
            "estimated_cv_years": cv_experience_years,
            "required_years": required_years,
            "fresh_graduate": cv_status["fresh_graduate"],
            "internship": cv_status["internship"],
            "project_experience": cv_status["project_experience"],
            "date_ranges_detected": [e["period"] for e in entry_periods],
            "score": exp_score, "status": exp_status,
            "period_details": entry_periods,
            "timeline_estimate_years": estimated_cv_years,
        },
        "education": {
            "cv_level": cv_level, "required_level": job_level,
            "cv_field": cv_field, "required_field": job_field,
            "score": edu_score, "status": edu_status,
        },
        "recommendations": recommendations,
        "scoring_info": {
            "base_weights": {"semantic": WEIGHT_SEMANTIC, "skill": WEIGHT_SKILL,
                             "experience": WEIGHT_EXPERIENCE, "education": WEIGHT_EDUCATION},
            "available_components": available,
            "observed_weight": round(sum(w for k, w in (
                ("semantic", WEIGHT_SEMANTIC), ("skill", WEIGHT_SKILL),
                ("experience", WEIGHT_EXPERIENCE), ("education", WEIGHT_EDUCATION),
            ) if available[k]), 2),
            "interpretation": "Heuristic CV-job matching score; not hiring probability",
        },
    }


if __name__ == "__main__":
    print("ICM Feature 1 module loaded; call analyze_cv_job() from Django service.")
