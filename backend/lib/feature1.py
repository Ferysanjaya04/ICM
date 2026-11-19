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

from .cv_understanding import ALIASES as SKILL_ALIASES, semantic_cv_representation, asserted_clauses, canonical_skill, evidence_excerpt, understand_cv, understand_education

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
SHORT_PERIOD_PATTERN = re.compile(rf"(?<!\w)(?P<sm>{MONTH_PATTERN})\.?\s*[-–—]\s*(?P<em>{MONTH_PATTERN})\.?\s+(?P<year>(?:19|20)\d{{2}})(?!\w)", re.I)
# Backward-compatible exported regex constants.
DATE_RANGE_PATTERN = PERIOD_PATTERN
YEAR_RANGE_PATTERN = re.compile(
    rf"\b(?:19|20)\d{{2}}\s*[-–—]\s*(?:(?:19|20)\d{{2}}|(?:{CURRENT_PATTERN}))\b",
    re.IGNORECASE,
)

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
    "teknologi rekayasa komputer", "data science", "cybersecurity", "cyber security", "electrical engineering",
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
    return canonical_skill(skill)


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
        r"\b(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|work\s+)?experience\b",
        r"\b(?:professional\s+|work\s+)?experience\s*[:\-]\s*(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        r"\b(\d+(?:[.,]\d+)?)\s*\+?\s*tahun\s+(?:pengalaman|bekerja|kerja)\b",
        r"\b(?:pengalaman(?:\s+(?:kerja|profesional))?|minimal|minimal pengalaman)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)\s*\+?\s*tahun\b",
        r"\b(?:minimum|at least|minimal|min\.)\s*(\d+(?:[.,]\d+)?)\s*\+?\s*(?:years?|yrs?|tahun)\b",
    )
    # Mask complete ranges before single-value matching: the upper bound is not
    # an exact CV claim. Job requirements retain the existing lower-bound policy.
    range_pattern = r"\b(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:years?|yrs?|tahun)(?:\s+(?:of\s+)?(?:experience|pengalaman))?\b"
    values: List[float] = []
    for match in re.finditer(range_pattern, normalized):
        low, high = (float(raw.replace(",", ".")) for raw in match.groups())
        if prefer_min and 0 <= low <= high <= 60:
            values.append(low)
    normalized = re.sub(range_pattern, " ", normalized)
    for pattern in patterns:
        for raw in re.findall(pattern, normalized):
            value = float(raw.replace(",", "."))
            if 0 <= value <= 60:
                values.append(value)
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
        short = SHORT_PERIOD_PATTERN.search(period)
        if short and MONTHS[short.group("sm").lower()] <= MONTHS[short.group("em").lower()]:
            return parse_period(f"{short.group('sm')} {short.group('year')} - {short.group('em')} {short.group('year')}")
        return empty
    start_year = int(match.group("start_year"))
    start_month = MONTHS.get(match.group("start_month").lower()) if match.group("start_month") else None
    today = date.today()
    if match.group("current"):
        end_year, end_month = today.year, today.month
    else:
        end_year = int(match.group("end_year"))
        end_month = MONTHS.get(match.group("end_month").lower()) if match.group("end_month") else None
    if (start_year > today.year or end_year > today.year or end_year < start_year
        or (start_month is not None and (start_year, start_month) > (today.year, today.month))
        or (end_month is not None and (end_year, end_month) > (today.year, today.month))):
        return empty
    if (start_month is None) != (end_month is None):
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


def extract_entry_periods(text: str, profile=None) -> List[Dict[str, Any]]:
    """Use understanding's entry categories; never reclassify projects as work."""
    if not isinstance(text, str) or not text.strip():
        return []
    profile = profile if profile is not None else understand_cv(text, {}, matching_context=True)
    lines = text.splitlines()
    records = {}
    for source, key in (("work", "work_entries"), ("internship", "internships"), ("project", "projects"), ("freelance", "freelance_entries")):
        for record in profile["experience"].get(key,[]):
            records[record["line"]] = (source, record)
    for record in profile["education"]["evidence"]:
        records.setdefault(record["line"], ("education", record))
    results = []
    for number, (category, record) in sorted(records.items()):
        if not record.get("duration_eligible", True):
            continue
        line = " ; ".join(asserted_clauses(lines[number - 1].strip()))
        for match in sorted(list(PERIOD_PATTERN.finditer(line)) + list(SHORT_PERIOD_PATTERN.finditer(line)), key=lambda m: m.start()):
            parsed = parse_period(match.group(0))
            if parsed["duration_months"] is None:
                continue
            remainder = (line[:match.start()] + " " + line[match.end():]).strip(" -–—|:,")
            preceding = lines[number - 2].strip() if number > 1 and records.get(number - 1, (None,))[0] == category else ""
            title = remainder or preceding or "Unspecified entry"
            results.append({
                "title": title[:200], "category": category, "period": match.group(0),
                "line": number, "engagement_type": record.get("engagement_type"), **parsed,
                "precision": "month" if parsed["start_month"] and parsed["end_month"] else "year_estimate",
            })
    return results


def _unique_work_months(entries: List[Dict[str, Any]], categories=("work",)) -> int:
    """Union of dated months for selected categories; professional work by default."""
    month_ids = set()
    for entry in entries:
        if entry["category"] not in categories:
            continue
        months = entry.get("duration_months")
        if not isinstance(months, int) or months <= 0:
            continue
        if entry.get("start_month") is None or entry.get("end_month") is None:
            continue  # Year-only spans are estimates, not verified month-duration evidence.
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


def get_education_level(text: str) -> int:
    """Legacy numeric sentinel; education inference is shared and evidence-based."""
    if not isinstance(text,str) or not text.strip():return 0
    return {None:0,'diploma':1,'bachelor':2,'master':3,'phd':4}[understand_education(text)['level']]


def get_education_field(text: str) -> Optional[str]:
    if not isinstance(text,str) or not text.strip():return None
    return understand_education(text)['field']


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
        return None, "Internship evidence available; professional duration insufficient or unknown"
    if cv_status.get("project_experience", False) or job_accepts_portfolio:
        return None, "Project experience detected; professional duration unavailable"
    return None, "Work experience not detected; duration unavailable"


def _study_field_key(value):
    # Translation equivalents only; related disciplines remain distinct.
    return {'ilmu komputer':'computer science','teknologi informasi':'information technology',
            'sistem informasi':'information systems','rekayasa perangkat lunak':'software engineering',
            'teknik komputer':'computer engineering','matematika':'mathematics','statistika':'statistics'}.get(value,value)


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
        if _study_field_key(cv_field) == _study_field_key(job_field):
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


def _scoring_metadata(scores):
    weights = {"semantic": WEIGHT_SEMANTIC, "skill": WEIGHT_SKILL,
               "experience": WEIGHT_EXPERIENCE, "education": WEIGHT_EDUCATION}
    available = {name: score is not None for name, score in scores.items()}
    observed = sum(weight for name, weight in weights.items() if available[name])
    return {
        "base_weights": weights,
        "available_components": available,
        "observed_weight": round(observed, 2),
        "effective_weights": {
            name: round(weight / observed, 6) if available[name] and observed > 0 else None
            for name, weight in weights.items()
        },
        "assessment_status": "complete" if all(available.values()) else (
            "partial" if any(available.values()) else "undetermined"
        ),
        "unknown_components": [name for name, measured in available.items() if not measured],
        "aggregation": "sum(score * base_weight for available components) / observed_weight",
        "skill_score_interpretation": "Coverage of recognized required skills only; consult job_understanding.requirement_coverage for unresolved items. Requirement recognition coverage is separate from observed_weight. 0 is not proof of no ability.",
        "interpretation": "Heuristic score for measured components only; not hiring probability or proof of absent ability",
    }


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


def _job_fragments(text):
    headings = {
        'required skills': ('required','skills'), 'skills': ('required','skills'),
        'keahlian wajib': ('required','skills'), 'keterampilan wajib': ('required','skills'),
        'requirements': ('required','skills'), 'required': ('required','skills'),
        'job requirements': ('required','general'), 'qualifications': ('required','general'),
        'persyaratan': ('required','general'), 'kualifikasi': ('required','general'),
        'experience requirements': ('required','experience'), 'experience': ('required','experience'),
        'pengalaman': ('required','experience'), 'syarat pengalaman': ('required','experience'),
        'education requirements': ('required','education'), 'education': ('required','education'),
        'pendidikan': ('required','education'), 'syarat pendidikan': ('required','education'),
        'preferred skills': ('preferred','skills'), 'preferred': ('preferred','general'),
        'nice to have': ('preferred','general'), 'nilai tambah': ('preferred','general'),
        'diutamakan': ('preferred','general'), 'responsibilities': ('responsibilities','general'),
        'tanggung jawab': ('responsibilities','general'), 'job description': ('responsibilities','general'),
        'deskripsi pekerjaan': ('responsibilities','general'), 'job title': ('administrative','general'),
    }
    section,context='unclassified','general'
    for number,raw in enumerate(text.splitlines(),1):
        # Strip presentation markup, never skill punctuation such as C#, C++, CI/CD.
        raw=re.sub(r'\*\*(.*?)\*\*|__(.*?)__',lambda m:m.group(1) or m.group(2),raw)
        raw=re.sub(r'^\s*#{1,6}\s+','',raw)
        for fragment in re.split(r';|(?<=\.)\s+',raw):
            fragment=re.sub(r'^\s*(?:[•*\-]|\d+[.)])\s*','',fragment).strip()
            if not fragment:continue
            prefix,sep,remainder=fragment.partition(':')
            key=normalize_text(prefix)
            if key in headings:
                section,context=headings[key];fragment=remainder.strip() if sep else ''
                if not fragment:continue
            kind=section
            if re.search(r'\b(?:preferred|optional|nice[- ]to[- ]have|diutamakan|nilai tambah|lebih disukai)\b',fragment,re.I):kind='preferred'
            elif re.search(r'\b(?:must|required|requires|membutuhkan|memerlukan|minimum|at least|minimal|wajib|harus)\b',fragment,re.I) and section not in {'preferred','responsibilities'}:kind='required'
            elif section=='unclassified' and re.match(r'(?:build|develop|maintain|design|membangun|mengembangkan|memelihara)\b',fragment,re.I):kind='responsibilities'
            local_context='skills' if re.match(r'^(?:must\s+(?:have|know|use)|harus\s+menguasai|wajib\s+menguasai|menguasai|proficient\s+in|experience\s+with)\s+',fragment,re.I) else context
            if local_context=='skills' and context!='skills' and kind=='required':
                section,context='required','skills'
            yield kind,{'line':number,'evidence':evidence_excerpt(fragment),'context':local_context}


def _positive_requirement_clauses(text):
    positive=asserted_clauses(text)
    if positive:return positive
    representation=semantic_cv_representation(text)
    return [representation['text']] if representation['metadata']['filter_applied'] and representation['metadata']['asserted_text_available'] else []


def _required_items(records,skills_db):
    vocabulary={normalize_skill(s) for values in skills_db.values() for s in values}
    items=[];seen=set()
    for record in records:
        if record['context'] in {'education','experience'}:continue
        for clause in _positive_requirement_clauses(record['evidence']):
            # Education/duration prose is assessed separately, never counted as skills.
            if re.search(r'\b(?:degree|bachelor|sarjana|diploma|s[123]|d[1234]|years?|tahun)\b',clause,re.I):continue
            clean=re.sub(r'^(?:(?:selain itu\s+)?(?:membutuhkan|memerlukan|requires?)|must\s+(?:have|know|use)|harus\s+menguasai|wajib\s+menguasai|menguasai|proficient\s+in|experience\s+with)\s+','',clause,flags=re.I)
            for atom in re.split(r'[,|]|\s+(?:and|dan)\s+',clean,flags=re.I):
                atom=atom.strip(' .:')
                if not atom:continue
                exact=normalize_skill(atom)
                known=[exact] if exact in vocabulary else extract_skills(atom,skills_db)
                if exact not in vocabulary and known:
                    # A longer term owns its span: DRF is not two independent
                    # requirements merely because its full name contains Django.
                    spans=[]
                    for term in set(known)|{a for a,c in SKILL_ALIASES.items() if c in known}:
                        for m in re.finditer(r'(?<!\w)'+re.escape(term)+r'(?!\w)',normalize_text(atom)):
                            spans.append((m.start(),m.end(),normalize_skill(term)))
                    chosen=[]
                    for start,end,name in sorted(spans,key=lambda v:(-(v[1]-v[0]),v[0])):
                        if not any(start<right and end>left for left,right,_ in chosen):chosen.append((start,end,name))
                    known=sorted({name for _,_,name in chosen})
                if record['context']=='skills' and known and exact not in vocabulary:
                    residual=normalize_text(atom)
                    variants=list(vocabulary)+[a for a,c in SKILL_ALIASES.items() if c in vocabulary]
                    for term in sorted(variants,key=len,reverse=True):
                        residual=re.sub(r'(?<!\w)'+re.escape(term)+r'(?!\w)',' ',residual)
                    residual=re.sub(r'\b(?:knowledge|skills?|experience|with|in|of|using|development|familiarity|required|must|know|have|menguasai|wajib|harus)\b',' ',residual)
                    if re.search(r'\w',residual):known=[]
                # Only explicit list/skill slots can assert exhaustive item counts.
                if record['context']!='skills' and not known:continue
                if '/' in atom and exact not in vocabulary:known=[] # Unreviewed slash alternatives are unresolved, not AND/OR guesses.
                identity=('known',tuple(known)) if known else ('unknown',normalize_text(atom))
                if identity in seen:continue
                seen.add(identity)
                items.append({'text':evidence_excerpt(atom),'line':record['line'],'skills':known,
                              'status':'recognized' if known else 'unresolved'})
    return items


def _experience_requirement(records):
    text='\n'.join(x['evidence'] for x in records)
    positive='\n'.join(c for r in records for c in _positive_requirement_clauses(r['evidence']))
    years=extract_explicit_experience_years(positive,prefer_min=True)
    n=normalize_text(text)
    waiver=bool(re.search(r'(?:no\s+(?:professional\s+|full[- ]time\s+)?(?:work\s+)?experience\s+(?:is\s+)?required|(?:professional|full[- ]time)[^.\n;]{0,65}not\s+(?:required|mandatory)|pengalaman[^.\n;]{0,65}tidak\s+(?:diperlukan|diwajibkan))',n))
    accepted=[]
    for kind,pattern in [('freelance',r'freelanc\w*|contract\w*'),('internship',r'intern\w*|magang'),('project',r'projects?|proyek|projek|laborator\w*')]:
        for clause in [normalize_text(record['evidence']) for record in records]:
            pieces=re.split(',',clause) if re.search(r'\b(?:not|never|tidak|bukan)\b',clause) else [clause]
            if any(re.search(pattern,piece) and re.search(r'accept\w*|welcome|eligible|diterima|diperbolehkan',piece) and not re.search(r'\b(?:not|never|tidak|bukan)\b',piece) for piece in pieces):
                accepted.append(kind);break
    year_clauses=[c for c in re.split(r'[.;\n]',positive) if extract_explicit_experience_years(c,True) is not None]
    scope='full_time' if any(re.search(r'full[- ]time|penuh waktu',c,re.I) for c in year_clauses) else ('professional' if any(re.search(r'professional|profesional',c,re.I) for c in year_clauses) else 'relevant')
    allowed=['work']+(accepted if scope=='relevant' else [])
    return {'status':'minimum_duration' if years is not None else ('waived' if waiver else ('conditional' if accepted or re.search(r'fresh.graduate|final.year|lulusan baru',n) else 'absent')),
            'minimum_years':years if years is not None else (0.0 if waiver else None),
            'duration_scope':scope,'accepted_types':accepted,'duration_types':allowed,
            'fresh_graduate_accepted':bool(re.search(r'fresh.graduate|lulusan baru',n)),
            'evidence':records}


def understand_job_requirements(text,skills_db):
    groups={k:[] for k in ['required','preferred','responsibilities','unclassified']}
    for kind,record in _job_fragments(text):
        if kind in groups:groups[kind].append(record)
    skill_groups={k:extract_skills('\n'.join(c for r in records for c in _positive_requirement_clauses(r['evidence'])),skills_db) for k,records in groups.items()}
    explicit=any(r['context']=='skills' for r in groups['required'])
    scoring_records=groups['required'] if explicit else groups['required']+groups['unclassified']
    items=_required_items(scoring_records,skills_db)
    scoring=sorted({s for item in items for s in item['skills']})
    if not explicit and not items:scoring=sorted(set(skill_groups['required'])|set(skill_groups['unclassified']))
    # Preserve unknown item slots, rather than treating them as matched or missing.
    recognized=sum(x['status']=='recognized' for x in items)
    coverage={'total':len(items),'recognized':recognized,'unresolved':len(items)-recognized,
              'recognition_coverage':recognized/len(items) if items and explicit else None,
              'enumeration_status':'explicit_skill_items' if explicit else 'non_exhaustive_prose',
              'items':items}
    records=groups['required']+groups['unclassified']
    positive='\n'.join(c for r in records for c in _positive_requirement_clauses(r['evidence']))
    edu=understand_education(positive,requirement_context=True) if positive.strip() else {'level':None,'reported_level':None,'field':None,'fields':[],'entries':[]}
    education_records=[r for r in records if r['context']=='education' or re.search(r'\b(?:degree|bachelor|sarjana|s[123]|d[1234]|diploma)\b',r['evidence'],re.I)]
    edu_text='\n'.join(x['evidence'] for x in education_records)
    accepts_progress=bool(re.search(r'currently pursuing|final.year|mahasiswa.*(?:akhir|diterima)|sedang.*(?:menempuh|ditempuh)',edu_text,re.I))
    required_level=edu.get('level') or (edu.get('reported_level') if accepts_progress else None)
    completion_required=bool(re.search(r'completed|graduated|lulus|selesai',edu_text,re.I)) and not accepts_progress
    experience_records=[r for r in records if r['context']=='experience' or re.search(r'\b(?:experience|pengalaman|years?|tahun|internships?|magang|freelance)\b',r['evidence'],re.I)]
    experience=_experience_requirement(experience_records)
    warnings=[]
    if groups['unclassified']:warnings.append('Unclassified prose is ambiguous; only disclosed recognized terms are assessed.')
    if scoring and not explicit:warnings.append('Free prose requirements are not exhaustively enumerated; recognition coverage is unknown.')
    if coverage['unresolved']:warnings.append('Some explicit skill requirements remain unresolved; recognized-skill score does not assess those items.')
    return {'schema_version':'requirements_v2','required_skills':sorted({s for i in _required_items(groups['required'],skills_db) for s in i['skills']}),
            'preferred_skills':skill_groups['preferred'],'responsibility_skills':skill_groups['responsibilities'],
            'unclassified_skills':skill_groups['unclassified'],'scoring_skills':scoring,
            'classification_status':'ambiguous' if groups['unclassified'] else 'structured',
            'scoring_policy':'Equal set coverage of recognized required skills; unresolved item slots are unknown, not matched/missing. Preferred/responsibilities excluded.',
            'warnings':warnings,'evidence':groups,'requirement_coverage':coverage,
            'experience_years':experience['minimum_years'],'experience_requirement':experience,
            'education_level':{None:0,'diploma':1,'bachelor':2,'master':3,'phd':4}[required_level],
            'education_field':edu.get('field'),'education_requirement':{'level':required_level,'fields':edu.get('fields',[]),'completion_required':completion_required,'accepts_in_progress':accepts_progress,'evidence':education_records}}


def analyze_cv_job(
    cv_text: str, job_text: str, cv_filename: Optional[str] = None,
    skills_db_path: Optional[str] = None, model_manager=None,
) -> Dict[str, Any]:
    """Return the legacy result schema used by AnalysisService._process_feature1_result."""
    if not isinstance(cv_text, str) or not cv_text.strip():
        raise ValueError("CV text tidak boleh kosong")
    if not isinstance(job_text, str) or not job_text.strip():
        raise ValueError("Job text tidak boleh kosong")

    # Preserve original CV line numbers for evidence; semantic encoding strips its inputs.
    job_text = job_text.strip()
    skills_db = load_skills_database(skills_db_path)
    profile = understand_cv(cv_text, skills_db, matching_context=True)
    cv_skills = [item["name"] for item in profile["skills"]]
    job_understanding = understand_job_requirements(job_text, skills_db)
    job_skills = job_understanding["scoring_skills"]
    supported_skills=set(cv_skills)
    if 'html/css' in supported_skills:supported_skills.update({'html','css'})
    if {'html','css'} <= supported_skills:supported_skills.add('html/css')
    matched_skills = sorted(supported_skills & set(job_skills))
    missing_skills = sorted(set(job_skills) - supported_skills)
    skill_score = calculate_skill_score(matched_skills, job_skills)
    req_coverage=job_understanding['requirement_coverage']
    for item in req_coverage['items']:
        if item['status']=='recognized':item['status']='matched' if set(item['skills']) <= set(matched_skills) else 'unmatched'
    req_coverage['matched']=sum(i['status']=='matched' for i in req_coverage['items'])
    req_coverage['unmatched']=sum(i['status']=='unmatched' for i in req_coverage['items'])

    cv_status = detect_career_status(cv_text)
    cv_status["internship"] = bool(profile["experience"]["internships"])
    cv_status["project_experience"] = bool(profile["experience"]["projects"])
    entry_periods = extract_entry_periods(cv_text, profile)
    raw_lines = cv_text.splitlines()
    claims = []
    for record in profile["experience"]["work_entries"]:
        if record["duration_eligible"]:
            for clause in asserted_clauses(raw_lines[record["line"] - 1]):
                years = extract_explicit_experience_years(clause)
                if years is not None:
                    numeric = re.search(r"\b\d+(?:[.,]\d+)?\s*(?:years?|yrs?|tahun)", normalize_text(clause))
                    claims.append({
                        "years": years, "line": record["line"],
                        "evidence": evidence_excerpt(clause, numeric.start() if numeric else 0),
                    })
    cv_explicit_years = max((claim["years"] for claim in claims), default=None)
    duration_months = _unique_work_months(entry_periods)
    internship_months = _unique_work_months(entry_periods, ("internship",))
    estimated_cv_years = round(duration_months / 12, 2) if duration_months else None
    # Dated professional entries take precedence over uncorroborated aggregate claims.
    cv_experience_years = estimated_cv_years if estimated_cv_years is not None else cv_explicit_years
    profile["experience"].update({
        "professional_years": cv_experience_years,
        "internship_months": internship_months if internship_months else None,
        "duration_basis": "dated_professional_entries" if estimated_cv_years is not None else (
            "explicit_professional_claim" if cv_explicit_years is not None else "unknown"
        ),
        "duration_claims": claims,
    })
    required_years = job_understanding["experience_years"]
    accepts_fresh = any(p in normalize_text(job_text) for p in FRESH_GRADUATE_PHRASES)
    accepts_portfolio = any(p in normalize_text(job_text) for p in PORTFOLIO_PHRASES)
    exp_requirement = job_understanding['experience_requirement']
    eligible_periods = entry_periods
    if exp_requirement['duration_scope']=='full_time':
        eligible_periods=[p for p in entry_periods if p.get('engagement_type')=='full_time']
    eligible_months=_unique_work_months(eligible_periods,exp_requirement['duration_types'])
    eligible_years=round(eligible_months/12,2) if eligible_months else (cv_explicit_years if exp_requirement['duration_scope']!='full_time' else None)
    exp_score, exp_status = calculate_experience_score(
        eligible_years, required_years, cv_status, accepts_fresh, accepts_portfolio,
    )
    observed_types={p['category'] for p in entry_periods}
    if profile['experience'].get('internships'):observed_types.add('internship')
    if profile['experience'].get('projects'):observed_types.add('project')
    if profile['experience'].get('freelance_entries'):observed_types.add('freelance')
    exp_eligibility = ('waived' if exp_requirement['status']=='waived' else
        ('accepted_evidence' if observed_types & set(exp_requirement['accepted_types']) else 'insufficient_evidence'))
    if exp_requirement['status']=='absent':exp_eligibility='requirement_absent'
    if exp_requirement['status']=='minimum_duration':exp_eligibility='requirement_met' if exp_score==100 else ('requirement_unmet' if exp_score is not None else 'insufficient_evidence')
    if exp_requirement['status']=='conditional':exp_status='Accepted experience types assessed separately; minimum duration not specified'

    cv_level = {None: 0, "diploma": 1, "bachelor": 2, "master": 3, "phd": 4}[profile["education"]["level"]]
    cv_field = profile["education"]["field"]
    job_level, job_field = job_understanding["education_level"], job_understanding["education_field"]
    edu_requirement=job_understanding['education_requirement']
    candidate_education=profile['education']
    if cv_field is not None and any(_study_field_key(cv_field)==_study_field_key(field) for field in edu_requirement['fields']):job_field=cv_field
    if edu_requirement['accepts_in_progress'] and candidate_education['status']=='in_progress':
        cv_level={None:0,'diploma':1,'bachelor':2,'master':3,'phd':4}[candidate_education['reported_level']]
    edu_score, edu_status = calculate_education_score(cv_level, job_level, cv_field, job_field)
    if job_level and edu_requirement['completion_required'] and candidate_education['completion_status']!='completed':
        if candidate_education['completion_status']=='in_progress':edu_score,edu_status=0.0,'Completed degree required; candidate is still enrolled'
        else:edu_score,edu_status=None,'Degree completion evidence insufficient'
    if edu_score is not None and edu_requirement['accepts_in_progress'] and candidate_education['status']=='in_progress':
        edu_status += '; student eligibility, not a completed degree'
    semantic_input = semantic_cv_representation(cv_text)
    semantic_score = calculate_semantic_score(semantic_input["text"], job_text, model_manager)
    compatibility_score, compatibility_level = calculate_compatibility_score(
        semantic_score, skill_score, exp_score, edu_score,
    )
    recommendations = generate_recommendations(
        missing_skills, exp_status, edu_score, semantic_score, required_years,
    )
    if semantic_input["metadata"]["fallback_reason"]:
        recommendations.append(
            "Tidak tersedia teks klaim positif untuk representasi semantik. "
            "Input cosine asli dipertahankan; kemiripan teks ini bukan bukti kemampuan kandidat."
        )
    if req_coverage['unresolved']:
        recommendations.append(f"Hanya {req_coverage['recognized']} dari {req_coverage['total']} item required skill dikenali. {req_coverage['unresolved']} item belum dapat dinilai; skill score hanya mencakup persyaratan yang dikenali, bukan seluruh lowongan.")
    if exp_requirement['status'] in {'conditional','waived'}:
        recommendations.append(f"Syarat pengalaman: {exp_requirement['status']}; bukti kandidat: {exp_eligibility}. Ini bukan klaim tahun pengalaman penuh waktu.")
    if not job_skills:
        recommendations.append(
            "Skill requirement spesifik tidak terdeteksi pada lowongan; skill score tidak dihitung. "
            "Periksa deskripsi lowongan dan vocabulary keterampilan."
        )

    # Additional fields are additive; legacy keys remain unchanged.
    return {
        "feature": "cv_vs_job_requirement", "cv_file": cv_filename,
        "semantic_input": semantic_input["metadata"],
        "job_requirement_source": "text_input",
        "compatibility": {"score": compatibility_score, "level": compatibility_level},
        "scores": {"semantic": semantic_score, "skill": skill_score,
                   "experience": exp_score, "education": edu_score},
        "skills": {"cv": cv_skills, "job_requirement": job_skills,
                   "matched": matched_skills, "missing_or_not_detected": missing_skills,
                   "evidence": profile["skills"],
                   "excluded_mentions": profile["excluded_skill_mentions"]},
        "experience": {
            "explicit_cv_years": cv_explicit_years,
            "estimated_cv_years": cv_experience_years,
            "required_years": required_years, "requirement_status": exp_requirement["status"],
            "eligibility_status": exp_eligibility, "eligible_years": eligible_years,
            "duration_scope": exp_requirement["duration_scope"], "accepted_types": exp_requirement["accepted_types"],
            "fresh_graduate": cv_status["fresh_graduate"],
            "internship": cv_status["internship"],
            "project_experience": cv_status["project_experience"],
            "assessment_status": "unknown" if exp_score is None else ("requirement_met" if exp_score == 100 else "not_demonstrated"),
            "relevant_activity_note": "Project and internship periods are relevant evidence, excluded from professional-year requirement. Year-only period estimates do not verify month duration or full-time status.",
            "date_ranges_detected": [e["period"] for e in entry_periods],
            "score": exp_score, "status": exp_status,
            "period_details": entry_periods,
            "timeline_estimate_years": estimated_cv_years,
        },
        "education": {
            "assessment_status": "unknown" if edu_score is None else ("unknown" if job_field and not cv_field else ("requirement_met" if edu_score == 100 else "not_demonstrated")),
            "cv_level": cv_level, "required_level": job_level,
            "cv_field": cv_field, "required_field": job_field,
            "score": edu_score, "status": edu_status, "candidate_completion_status": candidate_education["completion_status"],
            "accepts_in_progress": edu_requirement["accepts_in_progress"], "completion_required": edu_requirement["completion_required"],
        },
        "recommendations": recommendations,
        "job_understanding": job_understanding,
        "cv_understanding": profile,
        "scoring_info": _scoring_metadata({
            "semantic": semantic_score, "skill": skill_score,
            "experience": exp_score, "education": edu_score,
        }),
    }


if __name__ == "__main__":
    print("ICM Feature 1 module loaded; call analyze_cv_job() from Django service.")
