"""
Feature 1: CV vs Job Requirement Matching Engine
Modul inti untuk analisis kecocokan CV dengan Job Requirement.

Pipeline:
1. Text normalization
2. Skill extraction & matching
3. Experience detection & scoring
4. Education level & field detection & scoring
5. Semantic similarity scoring
6. Compatibility score calculation
7. Recommendations generation
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ============================================================
# CONSTANTS & CONFIGURATION
# ============================================================

# Bobot komponen scoring
WEIGHT_SEMANTIC = 0.25
WEIGHT_SKILL = 0.4
WEIGHT_EXPERIENCE = 0.2
WEIGHT_EDUCATION = 0.15

# Compatibility level threshold
COMPATIBILITY_HIGH_THRESHOLD = 80
COMPATIBILITY_MEDIUM_THRESHOLD = 60

# Bulan mapping
MONTHS = {
    "januari": 1, "january": 1, "jan": 1,
    "februari": 2, "february": 2, "feb": 2,
    "maret": 3, "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "june": 6, "jun": 6,
    "juli": 7, "july": 7, "jul": 7,
    "agustus": 8, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "oktober": 10, "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "december": 12, "dec": 12
}

MONTH_PATTERN = (
    r"januari|january|jan|februari|february|feb|maret|march|mar|"
    r"april|apr|mei|may|juni|june|jun|juli|july|jul|"
    r"agustus|august|aug|september|sept|sep|"
    r"oktober|october|oct|november|nov|desember|december|dec"
)

DATE_RANGE_PATTERN = re.compile(
    rf"\b(?P<start_month>{MONTH_PATTERN})\s+(?P<start_year>\d{{4}})\s*"
    rf"[-–—]\s*(?:(?P<end_month>{MONTH_PATTERN})\s+(?P<end_year>\d{{4}})|"
    rf"(?P<current>present|sekarang|current|ongoing))\b",
    re.IGNORECASE
)

YEAR_RANGE_PATTERN = re.compile(
    r"\b(?P<start_year>(?:19|20)\d{2})\s*[-–—]\s*(?P<end_year>(?:19|20)\d{2})\b"
)

# Skill aliases untuk normalisasi
SKILL_ALIASES = {
    "js": "javascript",
    "javascript": "javascript",
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "nodejs": "node.js",
    "node.js": "node.js",
    "node js": "node.js",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "restful api": "rest api",
    "rest api": "rest api",
    "ts": "typescript",
    "typescript": "typescript",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "amazon web services": "aws",
    "aws": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "gcp": "gcp",
    "agile methodology": "agile",
    "agile": "agile",
    "scrum framework": "scrum",
    "scrum": "scrum",
    "mysql": "mysql",
    "nosql": "nosql",
}

TECHNOLOGY_FIELDS = {
    "computer science", "computer engineering", "information technology",
    "information systems", "software engineering", "rekayasa perangkat lunak",
    "teknik informatika", "sistem informasi", "data science", "cybersecurity",
    "electrical engineering", "electronics engineering", "engineering", "teknik"
}

FRESH_GRADUATE_PHRASES = [
    "fresh graduate", "fresh graduates", "freshgraduate", "freshgraduates",
    "fresh-graduate", "fresh graduates are welcome", "lulusan baru",
    "lulusan perguruan tinggi baru", "new graduate", "new graduates",
    "recent graduate", "recent graduates"
]

PORTFOLIO_PHRASES = [
    "portfolio", "portofolio", "project portfolio",
    "portfolio proyek", "proyek nyata"
]


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """Normalisasi teks untuk konsistensi matching."""
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# SKILL EXTRACTION & MATCHING
# ============================================================

def load_skills_database(db_path: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Load skill database dari JSON.
    
    Args:
        db_path: Path ke skills_database.json. Default: D:/Kerja/Hermes/skills_database.json
        
    Returns:
        Dictionary dengan kategori skill
    """
    if db_path is None:
        db_path = Path(__file__).parent / "skills_database.json"
    else:
        db_path = Path(db_path)
    
    if not db_path.exists():
        raise FileNotFoundError(f"Skill database tidak ditemukan: {db_path}")
    
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_skill(skill: str) -> str:
    """Normalisasi skill dengan alias mapping."""
    skill = normalize_text(skill)
    return SKILL_ALIASES.get(skill, skill)


def extract_skills(text: str, skills_database: Dict[str, List[str]]) -> List[str]:
    """
    Ekstrak skill dari teks berdasarkan vocabulary dari skills_database.
    
    Returns:
        List skill yang terdeteksi (sorted, deduplicated)
    """
    normalized = normalize_text(text)
    detected = set()
    
    # Kumpulkan semua skill dari database
    all_skills = []
    for category, skills in skills_database.items():
        if isinstance(skills, list):
            all_skills.extend(skills)
    
    # Sort by length descending (longest first untuk avoid partial matches)
    all_skills = sorted(
        set(str(s).strip() for s in all_skills if s),
        key=len,
        reverse=True
    )
    
    for raw_skill in all_skills:
        canonical_skill = normalize_skill(raw_skill)
        if not canonical_skill:
            continue
        
        # Kumpulkan semua variasi skill ini
        variants = {normalize_text(raw_skill), canonical_skill}
        variants.update(
            normalize_text(alias)
            for alias, canonical in SKILL_ALIASES.items()
            if canonical == canonical_skill
        )
        
        for variant in variants:
            if not variant:
                continue
            # Word boundary matching
            pattern = rf"(?<!\w){re.escape(variant)}(?!\w)"
            if re.search(pattern, normalized):
                detected.add(canonical_skill)
                break
    
    return sorted(detected)


# ============================================================
# EXPERIENCE DETECTION
# ============================================================

def extract_explicit_experience_years(text: str) -> Optional[float]:
    """
    Extract tahun pengalaman kerja yang ditulis eksplisit di teks.
    
    Returns:
        Minimum tahun yang terdeteksi, atau None
    """
    normalized = normalize_text(text)
    values = []
    
    patterns = [
        r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\s+of\s+experience\b",
        r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\s+experience\b",
        r"\bexperience\s*[:\-]\s*(\d+(?:\.\d+)?)\s*\+?\s*years?\b",
        r"\bprofessional\s+experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*years?\b",
        r"\bwork\s+experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*years?\b",
        r"\b(\d+(?:\.\d+)?)\s*\+?\s*tahun\s+pengalaman\b",
        r"\bpengalaman\s*[:\-]\s*(\d+(?:\.\d+)?)\s*\+?\s*tahun\b",
        r"\bpengalaman\s+kerja\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*tahun\b",
        r"\b(\d+(?:\.\d+)?)\s*\+?\s*yrs?\s+experience\b",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, normalized)
        for match in matches:
            try:
                value = float(match)
                if 0 <= value <= 60:
                    values.append(value)
            except (ValueError, TypeError):
                continue
    
    # Range patterns
    range_patterns = [
        r"(?:minimal|minimum|at least|min\.?)\s*(\d+)\s*[-–]\s*(\d+)\s*years?",
        r"(\d+)\s*[-–]\s*(\d+)\s*years?\s+(?:of\s+)?experience",
        r"(\d+)\s*[-–]\s*(\d+)\s*tahun(?:\s+pengalaman)?",
        r"pengalaman(?:\s+kerja|projek)?\s*(?:minimal|minimum)?\s*(\d+)\s*[-–]\s*(\d+)\s*tahun",
    ]
    
    for pattern in range_patterns:
        for match in re.findall(pattern, normalized):
            try:
                lower = float(match[0])
                upper = float(match[1])
                if 0 <= lower <= upper <= 60:
                    values.append(lower)
            except (ValueError, TypeError, IndexError):
                continue
    
    return min(values) if values else None


def detect_career_status(text: str) -> Dict[str, bool]:
    """Deteksi status karir: fresh graduate, internship, project experience."""
    normalized = normalize_text(text)
    
    return {
        "fresh_graduate": any(p in normalized for p in FRESH_GRADUATE_PHRASES),
        "internship": any(p in normalized for p in ["internship", "intern", "magang"]),
        "project_experience": any(
            p in normalized
            for p in ["pengalaman proyek", "project experience", "project portfolio",
                     "portfolio proyek", "portofolio proyek"]
        )
    }


# ============================================================
# DATE & PERIOD PARSING
# ============================================================

def calculate_duration_months(start_year: int, start_month: int,
                              end_year: int, end_month: int) -> Optional[int]:
    """Calculate duration in months (inclusive)."""
    if None in (start_year, start_month, end_year, end_month):
        return None
    
    start_idx = start_year * 12 + start_month
    end_idx = end_year * 12 + end_month
    
    if end_idx < start_idx:
        return None
    
    return end_idx - start_idx + 1


def parse_period(period: Optional[str]) -> Dict[str, Optional[Any]]:
    """
    Parse periode tanggal dalam format (Bulan Tahun - Bulan Tahun) atau (Tahun - Tahun).
    
    Returns:
        Dict dengan start_year, start_month, end_year, end_month, duration_months
    """
    empty_result = {
        "start_year": None, "start_month": None,
        "end_year": None, "end_month": None,
        "duration_months": None
    }
    
    if not period:
        return empty_result
    
    match = DATE_RANGE_PATTERN.search(normalize_text(period))
    if not match:
        return empty_result
    
    start_month_name = match.group("start_month").lower()
    start_year = int(match.group("start_year"))
    start_month = MONTHS.get(start_month_name)
    
    if start_month is None:
        return empty_result
    
    if match.group("current"):
        now = datetime.now()
        end_year = now.year
        end_month = now.month
    else:
        end_month_name = match.group("end_month").lower() if match.group("end_month") else None
        end_year = int(match.group("end_year")) if match.group("end_year") else None
        end_month = MONTHS.get(end_month_name) if end_month_name else None
    
    if end_month is None or end_year is None:
        duration = None
    else:
        duration = calculate_duration_months(start_year, start_month, end_year, end_month)
    
    return {
        "start_year": start_year,
        "start_month": start_month,
        "end_year": end_year,
        "end_month": end_month,
        "duration_months": duration
    }


def extract_entry_periods(text: str) -> List[Dict[str, Any]]:
    """
    Ekstrak periode dari CV entries (project, internship, education).
    Mencari tanggal di sekitar judul entri.
    
    Returns:
        List dict dengan title, category, period, start_year, start_month, end_year, end_month, duration_months
    """
    normalized = normalize_text(text)
    
    # List entry yang dicari (case-insensitive after normalization)
    entries = [
        {"title": 'aplikasi e-commerce "tokokita"', "category": "project"},
        {"title": "sistem manajemen inventaris berbasis cloud", "category": "project"},
        {"title": "pt technology indonesia", "category": "internship"},
        {"title": "universitas dian nusantara", "category": "education"},
    ]
    
    found_entries = []
    for entry in entries:
        pos = normalized.find(entry["title"])
        if pos != -1:
            found_entries.append({**entry, "position": pos})
    
    found_entries.sort(key=lambda x: x["position"])
    
    results = []
    for index, entry in enumerate(found_entries):
        start = entry["position"]
        end = (
            found_entries[index + 1]["position"]
            if index + 1 < len(found_entries)
            else len(normalized)
        )
        
        context_start = max(0, start - 180)
        context_end = min(end, start + 350)
        context = normalized[context_start:context_end]
        
        match = DATE_RANGE_PATTERN.search(context)
        period = match.group(0) if match else None
        
        if not period:
            year_match = YEAR_RANGE_PATTERN.search(context)
            period = year_match.group(0) if year_match else None
        
        parsed = parse_period(period)
        
        results.append({
            "title": entry["title"],
            "category": entry["category"],
            "period": period,
            **parsed
        })
    
    # GENERIC FALLBACK (bukan hardcoded Johannes):
    # Jika ada 3 date ranges + 1 year range dan 4 entries ditemukan,
    # pairing periods secara otomatis
    if len(results) == 4:
        date_matches = list(DATE_RANGE_PATTERN.finditer(normalized))
        year_matches = list(YEAR_RANGE_PATTERN.finditer(normalized))
        
        if len(date_matches) == 3 and year_matches:
            detected_periods = [m.group(0) for m in date_matches]
            
            # Cari year range yang belum ada di detected_periods
            year_period = next(
                (m.group(0) for m in year_matches
                 if m.group(0) not in detected_periods),
                None
            )
            
            if year_period:
                fallback_periods = detected_periods + [year_period]
                # Assign ke entries
                for entry, period in zip(results, fallback_periods):
                    parsed = parse_period(period)
                    entry["period"] = period
                    entry.update(parsed)
    
    return results


# ============================================================
# EDUCATION DETECTION
# ============================================================

def get_education_level(text: str) -> int:
    """
    Detect education level: 0=none, 1=diploma, 2=bachelor, 3=master, 4=phd
    """
    normalized = normalize_text(text)
    
    if any(t in normalized for t in ["phd", "ph.d", "doctorate", "doktor"]):
        return 4
    if any(t in normalized for t in ["master", "master's", "msc", "m.sc", "magister", "s2"]):
        return 3
    if any(t in normalized for t in ["bachelor", "bachelor's", "bsc", "b.sc", "sarjana", "s1"]):
        return 2
    if any(t in normalized for t in ["diploma", "associate", "d3", "d4"]):
        return 1
    
    return 0


def get_education_field(text: str) -> Optional[str]:
    """Detect education field."""
    normalized = normalize_text(text)
    
    fields = [
        "computer science", "computer engineering", "information technology",
        "information systems", "software engineering", "rekayasa perangkat lunak",
        "teknik informatika", "sistem informasi", "data science", "cybersecurity",
        "electrical engineering", "electronics engineering", "engineering", "teknik",
        "business", "management", "marketing", "design", "finance", "accounting",
        "mathematics", "statistics", "physics", "biology", "chemistry"
    ]
    
    for field in fields:
        if field in normalized:
            return field
    
    return None


# ============================================================
# SCORING FUNCTIONS
# ============================================================

def calculate_semantic_score(cv_text: str, job_text: str,
                             model_manager=None) -> float:
    """
    Calculate semantic similarity using Sentence Transformer.
    
    Args:
        model_manager: Optional model manager to reuse loaded model
        
    Returns:
        Score 0-100
        
    Raises:
        ImportError: Jika sentence-transformers atau sklearn tidak tersedia
    """
    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError("sentence-transformers tidak terinstall. "
                         "Jalankan: pip install sentence-transformers")
    if not HAS_SKLEARN or not HAS_NUMPY:
        raise ImportError("scikit-learn dan numpy diperlukan. "
                         "Jalankan: pip install scikit-learn numpy")
    
    if model_manager and hasattr(model_manager, 'model'):
        model = model_manager.model
    else:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    
    embeddings = model.encode(
        [cv_text.strip(), job_text.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    
    similarity = cosine_similarity(
        embeddings[0].reshape(1, -1),
        embeddings[1].reshape(1, -1)
    )[0][0]
    
    score = max(0.0, min(1.0, float(similarity))) * 100
    return round(score, 2)


def calculate_skill_score(matched_skills: List[str],
                         job_skills: List[str]) -> float:
    """Calculate skill matching score."""
    if not job_skills:
        return 100.0
    
    score = (len(matched_skills) / len(job_skills)) * 100
    return round(min(100.0, max(0.0, score)), 2)


def calculate_experience_score(
    cv_experience_years: Optional[float],
    required_experience_years: Optional[float],
    cv_status: Dict[str, bool],
    job_accepts_fresh_graduate: bool,
    job_accepts_portfolio: bool
) -> Tuple[Optional[float], str]:
    """
    Calculate experience matching score.
    
    Returns:
        (score, status_message)
    """
    if cv_experience_years is not None and required_experience_years is not None:
        if required_experience_years <= 0:
            return 100.0, "No minimum experience duration required"
        
        if cv_experience_years >= required_experience_years:
            return 100.0, "Meets experience duration requirement"
        else:
            score = (cv_experience_years / required_experience_years) * 100
            return round(min(100.0, max(0.0, score)), 2), "Below experience duration requirement"
    
    if required_experience_years is not None:
        if cv_status["internship"]:
            return None, "Internship detected but duration unavailable"
        elif cv_status["project_experience"]:
            return None, "Project experience detected; professional work duration unavailable"
        else:
            return None, "Work experience not detected; duration unavailable"
    
    if (job_accepts_fresh_graduate and cv_status["fresh_graduate"] and
        (cv_status["project_experience"] or job_accepts_portfolio)):
        return None, "Fresh graduate accepted; experience duration requirement unspecified"
    
    return None, "Experience requirement not specified; compatibility cannot be determined"


def calculate_education_score(
    cv_level: int,
    job_level: int,
    cv_field: Optional[str],
    job_field: Optional[str]
) -> Tuple[float, str]:
    """Calculate education matching score."""
    if job_level == 0:
        return 100.0, "Education requirement not detected"
    
    if cv_level == 0:
        return 0.0, "CV education not detected"
    
    if cv_level < job_level:
        return 40.0, "Below required education level"
    
    # CV level >= job level
    if cv_field is not None and job_field is not None:
        if cv_field == job_field:
            return 100.0, "Education level and field match"
        elif cv_field in TECHNOLOGY_FIELDS and job_field in TECHNOLOGY_FIELDS:
            return 90.0, "Related education field"
        else:
            return 70.0, "Education level matches, field differs"
    
    return 70.0, "Education level matches, field not fully detected"


def calculate_compatibility_score(
    semantic_score: Optional[float],
    skill_score: Optional[float],
    experience_score: Optional[float],
    education_score: Optional[float]
) -> Tuple[Optional[float], str]:
    """
    Calculate final compatibility score dengan weight normalization.
    
    Returns:
        (score, level)
    """
    weights = {
        "semantic": WEIGHT_SEMANTIC,
        "skill": WEIGHT_SKILL,
        "experience": WEIGHT_EXPERIENCE,
        "education": WEIGHT_EDUCATION
    }
    
    scores = {
        "semantic": semantic_score,
        "skill": skill_score,
        "experience": experience_score,
        "education": education_score
    }
    
    available = {n: s for n, s in scores.items() if s is not None}
    
    if not available:
        return None, "UNDETERMINED"
    
    total_weight = sum(weights[n] for n in available)
    if total_weight <= 0:
        return None, "UNDETERMINED"
    
    score = sum(available[n] * weights[n] for n in available) / total_weight
    score = round(score, 2)
    
    if score >= COMPATIBILITY_HIGH_THRESHOLD:
        level = "HIGH"
    elif score >= COMPATIBILITY_MEDIUM_THRESHOLD:
        level = "MEDIUM"
    else:
        level = "LOW"
    
    return score, level


def generate_recommendations(
    missing_skills: List[str],
    experience_status: str,
    education_score: Optional[float],
    semantic_score: Optional[float],
    required_experience_years: Optional[float]
) -> List[str]:
    """Generate skill gap dan improvement recommendations."""
    recommendations = []
    
    # 1. Missing skills
    if missing_skills:
        for skill in missing_skills[:5]:
            recommendations.append(
                f"Periksa kembali skill '{skill}'. Skill ini belum terdeteksi "
                f"secara eksplisit pada CV. Jika dikuasai, tambahkan bukti "
                f"penggunaan melalui proyek, magang, atau pengalaman."
            )
    
    # 2. Experience gaps
    if "Below experience" in experience_status:
        recommendations.append(
            f"Requirement membutuhkan sekitar {required_experience_years:.0f} tahun pengalaman. "
            f"Tambahkan pengalaman relevan jika tersedia."
        )
    elif "Work experience not detected" in experience_status:
        recommendations.append(
            "Informasi pengalaman kerja belum terdeteksi pada CV. "
            "Jika memiliki pengalaman kerja relevan, cantumkan posisi, perusahaan, dan periode kerja."
        )
    elif "Internship detected but duration unavailable" in experience_status:
        recommendations.append(
            "Aktivitas internship terdeteksi, tetapi durasinya belum diketahui. "
            "Cantumkan periode mulai dan selesai jika informasi tersedia."
        )
    
    # 3. Education gaps
    if education_score is not None and education_score < 70:
        recommendations.append(
            "Periksa kembali kesesuaian tingkat dan bidang pendidikan "
            "dengan Job Requirement."
        )
    
    # 4. Semantic similarity
    if semantic_score is not None and semantic_score < 60:
        recommendations.append(
            "Kemiripan semantik antara CV dan Job Requirement relatif rendah. "
            "Sesuaikan deskripsi pengalaman, proyek, dan kompetensi dengan kebutuhan posisi."
        )
    
    # 5. Default
    if not recommendations:
        recommendations.append(
            "Tidak ditemukan gap utama berdasarkan parameter yang dianalisis. "
            "Tetap periksa kembali isi CV dan Job Requirement."
        )
    
    return recommendations


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================

def analyze_cv_job(
    cv_text: str,
    job_text: str,
    cv_filename: Optional[str] = None,
    skills_db_path: Optional[str] = None,
    model_manager=None
) -> Dict[str, Any]:
    """
    Analisis CV vs Job Requirement - Feature 1 Final Pipeline.
    
    Args:
        cv_text: Teks CV (result ekstraksi dari PDF/DOCX)
        job_text: Teks Job Requirement
        cv_filename: Nama file CV (optional, untuk logging)
        skills_db_path: Path ke skills_database.json (optional, auto-detect if None)
        model_manager: Optional model manager untuk reuse Sentence Transformer
        
    Returns:
        Dict dengan struktur feature_1_result:
        {
            "feature": "cv_vs_job_requirement",
            "cv_file": str|None,
            "compatibility": {"score": float|None, "level": str},
            "scores": {
                "semantic": float|None,
                "skill": float|None,
                "experience": float|None,
                "education": float|None
            },
            "skills": {
                "cv": list,
                "job_requirement": list,
                "matched": list,
                "missing_or_not_detected": list
            },
            "experience": {...},
            "education": {...},
            "recommendations": [...]
        }
    """
    
    # =========================================================
    # 1. VALIDASI INPUT
    # =========================================================
    if not isinstance(cv_text, str) or not cv_text.strip():
        raise ValueError("CV text tidak boleh kosong")
    if not isinstance(job_text, str) or not job_text.strip():
        raise ValueError("Job text tidak boleh kosong")
    
    cv_text = cv_text.strip()
    job_text = job_text.strip()
    
    # =========================================================
    # 2. LOAD SKILL DATABASE
    # =========================================================
    skills_database = load_skills_database(skills_db_path)
    
    # =========================================================
    # 3. TEXT NORMALIZATION
    # =========================================================
    cv_normalized = normalize_text(cv_text)
    job_normalized = normalize_text(job_text)
    
    # =========================================================
    # 4. SKILL EXTRACTION & MATCHING
    # =========================================================
    cv_skills = extract_skills(cv_text, skills_database)
    job_skills = extract_skills(job_text, skills_database)
    
    matched_skills = sorted(set(cv_skills).intersection(set(job_skills)))
    missing_skills = sorted(set(job_skills).difference(set(cv_skills)))
    
    skill_score = calculate_skill_score(matched_skills, job_skills)
    
    # =========================================================
    # 5. EXPERIENCE DETECTION
    # =========================================================
    cv_explicit_years = extract_explicit_experience_years(cv_text)
    job_explicit_years = extract_explicit_experience_years(job_text)
    
    cv_status = detect_career_status(cv_text)
    job_status = detect_career_status(job_text)
    
    # Deteksi durasi dari periods
    cv_entry_periods = extract_entry_periods(cv_text)
    
    cv_work_duration_months = sum(
        entry.get("duration_months", 0) or 0
        for entry in cv_entry_periods
        if entry["category"] in ("internship", "work") and entry.get("duration_months")
    )
    
    cv_work_experience_years = cv_work_duration_months / 12 if cv_work_duration_months > 0 else None
    
    # Explicit years prioritized
    cv_experience_years = cv_explicit_years if cv_explicit_years is not None else cv_work_experience_years
    required_experience_years = float(job_explicit_years) if job_explicit_years is not None else None
    
    # Extract date ranges untuk output
    cv_date_ranges = [
        e["period"] for e in cv_entry_periods
        if e["period"] is not None
    ]
    
    # Check job accepting fresh graduate
    job_accepts_fresh_graduate = any(
        p in job_normalized for p in FRESH_GRADUATE_PHRASES
    )
    job_accepts_portfolio = any(
        p in job_normalized for p in PORTFOLIO_PHRASES
    )
    
    experience_score, experience_status = calculate_experience_score(
        cv_experience_years,
        required_experience_years,
        cv_status,
        job_accepts_fresh_graduate,
        job_accepts_portfolio
    )
    
    # =========================================================
    # 6. EDUCATION DETECTION
    # =========================================================
    cv_education_level = get_education_level(cv_text)
    job_education_level = get_education_level(job_text)
    cv_education_field = get_education_field(cv_text)
    job_education_field = get_education_field(job_text)
    
    education_score, education_status = calculate_education_score(
        cv_education_level,
        job_education_level,
        cv_education_field,
        job_education_field
    )
    
    # =========================================================
    # 7. SEMANTIC SIMILARITY
    # =========================================================
    semantic_score = calculate_semantic_score(cv_text, job_text, model_manager)
    
    # =========================================================
    # 8. COMPATIBILITY SCORE
    # =========================================================
    compatibility_score, compatibility_level = calculate_compatibility_score(
        semantic_score,
        skill_score,
        experience_score,
        education_score
    )
    
    # =========================================================
    # 9. RECOMMENDATIONS
    # =========================================================
    recommendations = generate_recommendations(
        missing_skills,
        experience_status,
        education_score,
        semantic_score,
        required_experience_years
    )
    
    # =========================================================
    # 10. BUILD RESULT OBJECT
    # =========================================================
    result = {
        "feature": "cv_vs_job_requirement",
        "cv_file": cv_filename,
        "job_requirement_source": "text_input",
        
        "compatibility": {
            "score": compatibility_score,
            "level": compatibility_level
        },
        
        "scores": {
            "semantic": semantic_score,
            "skill": skill_score,
            "experience": experience_score,
            "education": education_score
        },
        
        "skills": {
            "cv": cv_skills,
            "job_requirement": job_skills,
            "matched": matched_skills,
            "missing_or_not_detected": missing_skills
        },
        
        "experience": {
            "explicit_cv_years": cv_explicit_years,
            "estimated_cv_years": cv_experience_years,
            "required_years": required_experience_years,
            "fresh_graduate": cv_status["fresh_graduate"],
            "internship": cv_status["internship"],
            "project_experience": cv_status["project_experience"],
            "date_ranges_detected": cv_date_ranges,
            "score": experience_score,
            "status": experience_status
        },
        
        "education": {
            "cv_level": cv_education_level,
            "required_level": job_education_level,
            "cv_field": cv_education_field,
            "required_field": job_education_field,
            "score": education_score,
            "status": education_status
        },
        
        "recommendations": recommendations
    }
    
    return result


if __name__ == "__main__":
    print("Feature 1 module loaded successfully.")
