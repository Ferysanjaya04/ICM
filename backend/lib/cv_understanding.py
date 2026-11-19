"""Deterministic CV evidence, shared canonical names, and cautious entry context.

No Django/model dependencies. A supported positive mention is a CV claim, not an
independent verification of competence. Absent evidence does not mean no ability.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ALIASES = {
    "html5": "html", "css3": "css", "drf": "django rest framework",
    "selenium webdriver": "selenium",
    "spark": "apache spark", "kafka": "apache kafka", "airflow": "apache airflow",
    "google bigquery": "bigquery", "apache pyspark": "pyspark",
    "rest apis": "rest api", "restful apis": "rest api",
    "reactjs": "react", "react.js": "react", "react js": "react",
    "nodejs": "node.js", "node js": "node.js",
    "postgres": "postgresql", "restful api": "rest api",
    "google cloud platform": "gcp", "google cloud": "gcp",
    "amazon web services": "aws", "k8s": "kubernetes",
    "js": "javascript", "ts": "typescript", "golang": "go",
    "agile methodology": "agile", "scrum framework": "scrum",
}
SECTION_ALIASES = {
    "personal project": "projects", "academic project": "projects", "proyek pribadi": "projects",
    "aktivitas dan hasil": "unspecified", "activities and results": "unspecified", "kegiatan teknis": "unspecified",
    "sertifikasi dan pelatihan": "certifications", "certifications and training": "certifications",
    "proyek tambahan": "projects", "selected projects": "projects", "academic projects": "projects",
    "ringkasan profesional": "summary", "batas kompetensi": "other", "batas pengalaman": "other",
    "selected freelance work": "freelance", "freelance work": "freelance",
    "freelance experience": "freelance", "pengalaman freelance": "freelance",
    "contract experience": "freelance", "pengalaman kontrak": "freelance",
    **{heading: "job_requirements" for heading in (
        "job requirements", "job description", "desired skills", "target position requirements",
        "skills required", "persyaratan lowongan", "kualifikasi yang dibutuhkan",
    )},
    "keahlian teknis": "skills",
    "spark": "apache spark", "kafka": "apache kafka", "airflow": "apache airflow",
    "google bigquery": "bigquery", "apache pyspark": "pyspark",
    "rest apis": "rest api", "restful apis": "rest api",
    "skills": "skills", "skill": "skills", "technical skills": "skills", "tech stack": "skills",
    "keahlian": "skills", "keterampilan": "skills", "kompetensi": "skills", "keterampilan teknis": "skills",
    "work experience": "work_experience", "professional experience": "work_experience",
    "experience": "work_experience", "employment": "work_experience", "employment history": "work_experience",
    "work history": "work_experience", "career history": "work_experience",
    "pengalaman": "work_experience", "pengalaman kerja": "work_experience",
    "pengalaman profesional": "work_experience", "riwayat pekerjaan": "work_experience",
    "internship": "internship", "internships": "internship", "magang": "internship",
    "pengalaman magang": "internship", "praktik kerja": "internship", "praktik kerja lapangan": "internship",
    "projects": "projects", "project": "projects", "personal projects": "projects", "project experience": "projects",
    "proyek": "projects", "projek": "projects", "pengalaman proyek": "projects", "portfolio": "projects", "portofolio": "projects",
    "education": "education", "academic background": "education", "pendidikan": "education", "riwayat pendidikan": "education",
    "certifications": "certifications", "certification": "certifications", "certificates": "certifications", "sertifikasi": "certifications",
    "summary": "summary", "professional summary": "summary", "profile": "summary", "profil": "summary", "ringkasan": "summary",
    "career objective": "objective", "objective": "objective", "tujuan karier": "objective",
    "tujuan karir": "objective", "career goals": "objective", "target role": "objective", "desired position": "objective",
    "contact": "contact", "kontak": "contact", "interests": "interests", "minat": "interests",
    "references": "other", "referensi": "other", "organizations": "other", "organisasi": "other",
}
NEGATION_CUE = re.compile(
    r"\b(?:no|not(?!\s+only\b)|never|without|lack(?:s|ing)?|cannot|\w+n['’]t|belum|tidak(?!\s+hanya\b)|tanpa|bukan)\b", re.I
)
ASPIRATION_CUE = re.compile(
    r"\b(?:want(?:s)? to|wish(?:es)? to|plan(?:ning)? to|hope(?:s)? to|interested in|"
    r"looking for|seeking|aspire to|aspiring|will (?:learn|use|study)|currently learning|learning to|"
    r"I am learning|I['’]m learning|we are learning|sedang mempelajari|"
    r"ingin|berencana|berminat|tertarik|akan (?:belajar|menggunakan|mempelajari)|sedang belajar)\b|"
    r"^(?:I am\s+)?(?:learning|belajar|mempelajari)\b", re.I
)
NEGATIVE_AFTER = re.compile(
    r"^[\s:,\-]*(?:(?:is|are|was|were|has|have|adalah|masih)\s+)?"
    r"(?:not|never|belum|tidak|bukan)\b", re.I
)
ASPIRATION_AFTER = re.compile(
    r"^[\s:,\-]*(?:(?:is|adalah)\s+)?(?:a skill (?:I |to )?|something I )?"
    r"(?:want to learn|wish to learn|plan to learn|to be learned|ingin dipelajari|akan dipelajari)", re.I
)
INTERN_TERMS = re.compile(r"\b(?:intern(?:ship)?|magang|pkl)\b", re.I)
PROJECT_TITLE = re.compile(
    r"(?:\b(?:personal|academic|capstone|side|student|university)\s+project\b|"
    r"\bproyek\s+(?:pribadi|kuliah|akademik)\b|^(?:project(?!\s+manager\b)|proyek|projek|portfolio|portofolio)\s*[:\-])", re.I
)
WORK_ROLE = re.compile(
    r"\b(?:developer|engineer|analyst|administrator|programmer|designer|technician|"
    r"consultant|scientist|manager|karyawan|pegawai|bekerja|staff|staf|freelancer)\b", re.I
)
WORK_DURATION = re.compile(r"\b(?:professional experience|work experience|pengalaman kerja|bekerja)\b", re.I)
ACTION = re.compile(r"\b(?:built|used|developed|implemented|created|designed|menggunakan|membangun|mengembangkan|membuat|menerapkan)\b", re.I)
DEGREE_PATTERNS = [
    ("phd", re.compile(r"\b(?:ph\.?d\.?|doctorate|doktor|s3)\b", re.I)),
    ("master", re.compile(r"\b(?:master(?:'s|s)?|m\.?sc\.?|magister|s2)\b", re.I)),
    ("bachelor", re.compile(r"\b(?:bachelor(?:'s|s)?|b\.?sc\.?|sarjana(?:\s+terapan)?|s1|d4)\b", re.I)),
    ("diploma", re.compile(r"\b(?:diploma|associate\s+degree|d[123])\b", re.I)),
]
FIELD_PATTERNS = sorted([
    "computer science", "ilmu komputer", "teknik informatika", "informatika", "teknologi rekayasa komputer",
    "information technology", "teknologi informasi", "information systems", "sistem informasi",
    "software engineering", "rekayasa perangkat lunak", "computer engineering", "teknik komputer",
    "data science", "cybersecurity", "cyber security", "electrical engineering", "mathematics",
    "matematika", "statistics", "statistika", "management", "manajemen", "accounting", "akuntansi",
], key=len, reverse=True)
IN_PROGRESS = re.compile(
    r"\b(?:pursuing|enrolled|currently studying|undergraduate|candidate|in progress|"
    r"expected|sedang (?:kuliah|menempuh|ditempuh)|semester akhir|final.year|mahasiswa|belum lulus|belum selesai|not yet completed|gelar belum diperoleh|rencana lulus)\b", re.I
)
COMPLETED = re.compile(r"\b(?:graduated|earned|completed|awarded|lulus|lulusan|menyelesaikan|selesai)\b", re.I)
MAX_MENTIONS_PER_SKILL = 5
MAX_EXCLUDED_MENTIONS = 1000


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def canonical_skill(name: str) -> str:
    normalized = _norm(name)
    return ALIASES.get(normalized, normalized)


# Keep compatibility for callers of the original helper.
_canonical = canonical_skill


def _vocabulary(skills_database: dict[str, list[str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for items in skills_database.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, str) or not item.strip():
                continue
            canonical = canonical_skill(item)
            result.setdefault(canonical, set()).update({_norm(item), canonical})
    for alias, canonical in ALIASES.items():
        if canonical in result:
            result[canonical].add(alias)
    return result


def _sections(text: str, matching_context=False):
    aliases = dict(SECTION_ALIASES)
    if matching_context:
        aliases.update({"training": "certifications", "courses": "certifications",
                        "pelatihan": "certifications", "kursus": "certifications",
                        "sertifikasi & pelatihan": "certifications",
                        "certifications & training": "certifications",
                        "pengalaman kerja (magang)": "internship",
                        "academic projects": "projects"})
    section = "unspecified"
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        heading = line.lstrip("•*- ").strip()
        pattern = r"^([\w /&()\-]{2,80})\s*:\s*(.*)$" if matching_context else r"^([\w /-]{2,40})\s*:\s*(.*)$"
        match = re.match(pattern, heading)
        if match and _norm(match.group(1)) in aliases:
            section = aliases[_norm(match.group(1))]
            if match.group(2).strip():
                yield line_number, section, match.group(2).strip()
            continue
        key = _norm(heading.rstrip(": "))
        if key in aliases:
            section = aliases[key]
            continue
        yield line_number, section, line


def _split_clauses(line: str):
    # Keep comma-separated negative/aspirational lists together. Split only sentence,
    # contrast, or explicit new positive predicates; dots within Node.js remain intact.
    return re.split(
        r"\s*(?:;|(?<=[.!?])\s+|\bbut\b|\bhowever\b|\btetapi\b|\bnamun\b|"
        r",\s*(?=(?:I\s+)?(?:built|used|developed|implemented|created|designed|menggunakan|membangun|mengembangkan|membuat|menerapkan)\b))\s*",
        line, flags=re.I,
    )


def _rejection(clause: str, start: int, end: int, source: str) -> str | None:
    if source == "job_requirements":
        return "job_requirement_context"
    if source in {"objective", "interests"}:
        return "aspiration"
    before, after = clause[:start], clause[end:]
    cues = [(m.start(), "negation") for m in NEGATION_CUE.finditer(before)]
    cues += [(m.start(), "aspiration") for m in ASPIRATION_CUE.finditer(before)]
    if cues:
        return max(cues)[1]
    if NEGATIVE_AFTER.search(after):
        return "negation"
    if re.search(r"\b(?:are|were)\s+(?:not|never)\b", after):
        return "negation"
    if ASPIRATION_AFTER.search(after):
        return "aspiration"
    return None


def _ambiguous_skill(canonical: str, variant: str, clause: str, source: str) -> bool:
    if canonical == "go":
        return variant != "golang" and source != "skills" and not re.search(
            r"\b(?:programming|language|developer|backend|golang)\b", clause, re.I
        )
    if variant in {"js", "ts", "ios", "isis"}:
        return source not in {"skills", "work_experience", "projects", "internship", "certifications"}
    return False


def skill_kind(name: str) -> str:
    """Type the claim without presenting every reference term as technology."""
    name = canonical_skill(name)
    if name in {"e-commerce", "ecommerce"}:
        return "industry_domain"
    if name in {"analytics", "big data", "database"}:
        return "general_concept"
    if name in {"scripting", "microservices", "agile", "scrum", "kanban"}:
        return "technical_method"
    if name in {
        "python", "sql", "postgresql", "scala", "bash", "apache spark", "pyspark",
        "apache airflow", "pandas", "dbt", "mongodb", "bigquery", "snowflake", "redis",
        "git", "docker", "kubernetes", "gcp", "aws", "apache kafka", "grafana",
        "django", "flask", "javascript", "typescript", "react", "html", "css",
        "linux", "wireshark", "nmap", "terraform", "rest api", "jwt",
    }:
        return "technology"
    return "reference_skill"


def _domain_context(canonical: str, clause: str, source: str) -> bool:
    # A project industry/title is not a claim of domain expertise. Explicit
    # skill listings or competence predicates remain eligible, typed as domain.
    return skill_kind(canonical) == "industry_domain" and source != "skills" and not re.search(
        r"\b(?:expertise in|proficient in|skilled in|menguasai|keahlian dalam)\b", clause, re.I
    )


def evidence_excerpt(text: str, start=0, end=0) -> str:
    # Long-clause matching uses normalized offsets: return an explicitly normalized
    # excerpt in that case, rather than a misleading slice of different-length text.
    if len(text) <= 400:
        return text
    normalized = _norm(text)
    left = max(0, start - 120)
    return normalized[left:max(left + 400, end)][:400]


def _source(section: str, line: str, previous: str | None) -> str:
    if section in {"job_requirements", "objective", "interests", "education", "skills", "certifications", "contact", "other"}:
        return section
    if section == "freelance":
        return "freelance"
    if re.search(r"\b(?:freelanc(?:e|er)|contractor|pekerja kontrak)\b", line, re.I) and not NEGATION_CUE.search(line):
        return "freelance"
    if INTERN_TERMS.search(line):
        return "internship"
    if PROJECT_TITLE.search(line) and not ACTION.search(line):
        return "projects"
    if re.search(r"\b(?:bachelors?|sarjana|s1|s2|s3|d[1234]|magister|phd|doctorate|master(?:'s)?\s+(?:of|in|degree))\b", line, re.I):
        return "education"
    if section in {"work_experience", "internship", "projects", "freelance"}:
        # Only an entry title can reset a preceding internship/project in a work
        # section. A bullet describing work on a project is not itself a new job.
        if section == "work_experience" and WORK_ROLE.search(line) and not ACTION.search(line):
            return "work_experience"
        return previous or section
    if WORK_DURATION.search(line) or WORK_ROLE.search(line):
        return "work_experience"
    if previous in {"work_experience", "internship", "projects", "freelance"} and (
        ACTION.search(line) or re.search(r"\b(?:19|20)\d{2}\b", line)
    ):
        return previous
    return section


def asserted_clauses(line: str):
    """Positive local statements only; unrelated negative sentences do not erase dates."""
    return [clause for clause in _split_clauses(line)
            if clause.strip() and not NEGATION_CUE.search(clause) and not ASPIRATION_CUE.search(clause)]


NON_DEGREE_CLAIM = re.compile(
    r"\b(?:courses?|coursework|training|certificat(?:e|es|ion|ions)|certified|kursus|pelatihan|sertifikat|sertifikasi|bootcamp|workshop)\b|"
    r"\b(?:bachelor(?:['’]s)?|master(?:['’]s)?|sarjana|s1)[\s\-‐‑–—]+(?:level|equivalent)\b|"
    r"\b(?:setara|tingkat|equivalent to)\s+(?:a\s+)?(?:bachelor|sarjana|s1)\b", re.I
)


def _non_degree_kinds(text):
    kinds = []
    for kind, pattern in (
        ('course', r'\b(?:courses?|coursework|kursus)\b'),
        ('training', r'\b(?:training|pelatihan|bootcamp|workshop)\b'),
        ('certification', r'\b(?:certified|certificat(?:e|es|ion|ions)|sertifikat|sertifikasi)\b'),
    ):
        if re.search(pattern,text,re.I):kinds.append(kind)
    return kinds or ['level_reference' if NON_DEGREE_CLAIM.search(text) else 'non_degree_context']


def _study_fields(text):
    """Explicit field names only, longest overlapping phrase wins."""
    matches = []
    for field in FIELD_PATTERNS + ['sains data']:
        for match in re.finditer(rf'(?<!\w){re.escape(field)}(?!\w)', _norm(text)):
            matches.append((match.start(), match.end(), 'data science' if field == 'sains data' else field))
    accepted = []
    for start,end,field in sorted(matches,key=lambda item: (-(item[1]-item[0]),item[0])):
        if not any(start < b and end > a for a,b,_ in accepted):accepted.append((start,end,field))
    return list(dict.fromkeys(field for _,_,field in sorted(accepted)))


def _education(records, matching_context=False, *, requirement_context=False):
    # matching_context is retained for private-call compatibility; education
    # policy is shared unconditionally by both features.
    entries, field_claims, non_degree, active = [], [], [], None
    for number, source, line in records:
        has_degree = False
        for clause in _split_clauses(line):
            if not clause.strip():continue
            normalized = _norm(clause)
            if source == 'certifications' or NON_DEGREE_CLAIM.search(clause):
                kinds = _non_degree_kinds(clause)
                non_degree.append({'kind':kinds[0],'kinds':kinds,'evidence':evidence_excerpt(clause.strip()),'line':number,'source':source})
                active = None # A later course completion must not complete an earlier degree.
                continue
            fields = _study_fields(clause)
            degree = next(((name,regex.search(normalized)) for name,regex in DEGREE_PATTERNS if regex.search(normalized)),None)
            if not degree:
                if fields and source not in {'objective','interests','job_requirements'} and (
                    source == 'education' or re.search(r'\b(?:graduate|graduated|lulusan|jurusan|bidang studi|studied|studying|major(?:ed)?|kuliah)\b',normalized)
                ) and not NEGATION_CUE.search(normalized) and not ASPIRATION_CUE.search(normalized):
                    field_claims.append({'fields':fields,'evidence':evidence_excerpt(clause.strip()),'line':number,'source':source})
                continue
            name,match = degree
            academic = name != 'master' or bool(re.search(
                r"\b(?:master(?:'s|s)?\s+(?:of|in|degree)|magister|s2|m\.?sc\.?)\b", normalized
            )) or (source == 'education' and fields and match.start()==0)
            if not academic:continue
            reference_to_others = re.search(r'\b(?:mentored|supervised|taught|hiring|recruiting|candidates|applicants|students|thesis|dissertation)\b',normalized)
            if requirement_context:
                reference_to_others = re.search(r'\b(?:mentored|supervised|taught|hiring|recruiting|students|thesis|dissertation)\b',normalized)
            own_claim = source == 'education' or match.start() == 0 or normalized[:match.start()].strip() in {'a','an','the'} or IN_PROGRESS.search(clause) or re.search(
                r'\b(?:I (?:have|hold)|holds?|earned|graduated|completed|lulusan|lulus|menyelesaikan|gelar|with)\b',normalized[:match.start()]
            )
            excluded_context = _rejection(normalized,match.start(),match.end(),source) or re.search(r'\b(?:applying for|apply for|akan menempuh)\b',normalized[:match.start()])
            if reference_to_others or not (own_claim or excluded_context):
                continue
            has_degree = True
            # Not yet graduated describes progress, not absence of enrollment.
            rejection_text = re.sub(r'\b(?:belum lulus|belum selesai|not yet graduated|not yet completed)\b',lambda m:' '*len(m.group()),normalized)
            reason = _rejection(rejection_text,match.start(),match.end(),source)
            if re.search(r'\b(?:applying for|apply for|akan menempuh)\b',normalized[:match.start()]):reason='aspiration'
            status = 'in_progress' if IN_PROGRESS.search(clause) or re.search(r'\bnot yet graduated\b',normalized) else (
                'completed' if COMPLETED.search(clause) else 'reported'
            )
            if reason:status='negated' if reason=='negation' else ('requirement_reference' if reason=='job_requirement_context' else 'aspiration')
            active={'level':name,'field':fields[0] if fields else None,'fields':fields,'status':status,
                    'completion_status':status if status in {'in_progress','completed'} else 'unknown',
                    'evidence':evidence_excerpt(clause.strip(),match.start(),match.end()),'line':number,'source':source,
                    'qualification_code': next((code for code in ['d4','d3','d2','d1','s1','s2','s3'] if re.search(r'\b'+code+r'\b',normalized)), name)}
            entries.append(active)
            active_followups = 0
        if not has_degree and source=='education' and active and active_followups < 3:
            active_followups += 1
            if IN_PROGRESS.search(line):
                active['status']='in_progress';active['completion_status']='in_progress'
                active['status_evidence']={'line':number,'evidence':evidence_excerpt(line)}
            elif COMPLETED.search(line) and not NEGATION_CUE.search(line) and not NON_DEGREE_CLAIM.search(line):
                active['status']='completed';active['completion_status']='completed'
                active['status_evidence']={'line':number,'evidence':evidence_excerpt(line)}
            if not active['field'] and not NON_DEGREE_CLAIM.search(line):
                fields=_study_fields(line)
                if fields:
                    active['field']=fields[0];active['fields']=fields
                    active['field_evidence']={'line':number,'evidence':evidence_excerpt(line)}
        if source!='education' and not has_degree:active=None
    levels={'diploma':1,'bachelor':2,'master':3,'phd':4}
    eligible=[entry for entry in entries if entry['status'] in {'reported','completed'}]
    selected=max(eligible,key=lambda e:(levels[e['level']],e['status']=='completed'),default=None)
    progressing=max((e for e in entries if e['status']=='in_progress'),key=lambda e:levels[e['level']],default=None)
    primary=selected or progressing
    fields=primary['fields'] if primary else (field_claims[0]['fields'] if field_claims else [])
    evidence={number:{'line':number,'evidence':evidence_excerpt(line)} for number,source,line in records if source=='education'}
    for entry in entries+field_claims:evidence.setdefault(entry['line'],{'line':entry['line'],'evidence':entry['evidence']})
    return {'policy_version':'ai4b.1','qualification_code':primary.get('qualification_code') if primary else None,'level':selected['level'] if selected else None,
            'reported_level':primary['level'] if primary else None,
            'field':fields[0] if fields else None,'fields':fields,
            'status':primary['status'] if primary else 'unknown',
            'completion_status':primary['completion_status'] if primary else 'unknown',
            'evidence':[evidence[number] for number in sorted(evidence)],'entries':entries,
            'field_claims':field_claims,'non_degree_claims':non_degree,
            'evidence_policy':'Explicit CV claims, not independent credential verification. In-progress level is reported_level only; unknown completion is not completed.'}


def understand_education(text, *, requirement_context=False):
    """One education result from original CV text, independent of skill lexicon/mode."""
    if not isinstance(text,str) or not text.strip():raise ValueError('Teks CV tidak boleh kosong')
    # Mixed headings are education context, but each clause must still establish
    # an academic claim. Courses in that section do not become degrees.
    education_text = re.sub(r'(?im)^(\s*)(?:education\s*(?:and|&)\s*certifications|pendidikan\s*(?:dan|&)\s*sertifikasi)(\s*:?)',r'\1Education\2',text)
    # Keep explicit section context here. _source() can infer education from a
    # keyword for activity grouping; that inference must not verify a credential.
    records=[(number,section,line) for number,section,line in _sections(education_text,matching_context=True)]
    if requirement_context:
        records=[(number,'education',line) for number,_,line in records]
    return _education(records,requirement_context=requirement_context)


def semantic_cv_representation(text: str) -> dict[str, Any]:
    """Local asserted text for MiniLM only; never rewrite classifier/OCR input.

    No technology/profession-specific penalties. Unchanged assertions retain the
    exact original string. If no asserted text remains, retain the original cosine input and report
    that limitation; never embed fabricated evidence or assign a numeric penalty.
    """
    kept = []
    removed = 0
    pending = False
    previous_number = 0
    previous_section = None
    raw_lines = text.splitlines()
    for number, section, line in _sections(text, matching_context=True):
        heading = _norm(raw_lines[number - 1].split(':', 1)[0].strip().lstrip('\u2022*- '))
        if number != previous_number + 1 or section != previous_section or heading in SECTION_ALIASES:
            pending = False
        previous_number, previous_section = number, section
        for clause in _split_clauses(line):
            if not clause.strip():
                continue
            if section in {'job_requirements', 'objective', 'interests'}:
                removed += 1
                continue
            if ACTION.search(clause) and not (NEGATION_CUE.search(clause) or ASPIRATION_CUE.search(clause)):
                pending = False
            cues = list(NEGATION_CUE.finditer(clause)) + list(ASPIRATION_CUE.finditer(clause))
            if cues:
                first = min(cues, key=lambda m: m.start())
                prefix = clause[:first.start()]
                # Preserve an explicit positive prefix in a mixed list, but not
                # the subject of a postfix negation ("Kubernetes is not...").
                boundary = re.search(r'(?:,\s*|\b(?:and|dan)\s+)$', prefix, re.I)
                if boundary and prefix[:boundary.start()].strip() and not pending:
                    kept.append(prefix[:boundary.start()].strip())
                elif first.group().casefold() in {"without", "tanpa"} and ACTION.search(prefix) and not pending:
                    kept.append(prefix.strip())
                elif re.search(r"\bwith\s+$", prefix, re.I) and ACTION.search(prefix) and not pending:
                    kept.append(re.sub(r"\bwith\s+$", "", prefix, flags=re.I).strip())
                removed += 1
                pending = bool(re.search(r'(?:\b(?:with|in|of|for|learn|learning|menguasai|menggunakan|mempelajari|belajar|keahlian|expertise|and|or|dan|atau)|[, :])$', clause.strip(), re.I))
            elif pending:
                removed += 1
            else:
                kept.append(clause.strip())
        if re.search(r'[.!?]$', line):
            pending = False
    filtered = '\n'.join(kept)
    fallback = removed > 0 and not filtered.strip()
    changed = removed > 0 and not fallback
    return {'text': filtered if changed else text,
            'metadata': {'policy_version': 'asserted_text_v1', 'filter_applied': changed,
                         'excluded_clause_count': removed,
                         'asserted_text_available': bool(filtered.strip()),
                         'fallback_reason': 'no_asserted_text' if fallback else None,
                         'interpretation': 'Cosine measures text similarity, not verified competence or hiring probability. Raw fallback without asserted text is not evidence of ability.'}}


def _local_project_claim(clause: str, source: str) -> bool:
    # Only explicit project + completed/used activity in an unassigned/summary
    # clause. A title/date alone cannot establish employment or competence.
    return source in {'unspecified', 'summary'} and bool(ACTION.search(clause)) and bool(
        re.search(r'\b(?:projects?|proyek|projek|capstone|tugas akhir|tugas kuliah|academic assignment)\b', clause, re.I)
    ) and not (NEGATION_CUE.search(clause) or ASPIRATION_CUE.search(clause) or re.search(
        r'\b(?:at work|employment|employed|professional|bekerja|pekerjaan|magang|intern(?:ship)?)\b', clause, re.I
    ))


def understand_cv(text: str, skills_database: dict[str, list[str]], *, matching_context=False) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Teks CV tidak boleh kosong")
    if not isinstance(skills_database, dict):
        raise ValueError("skills_database harus berupa dictionary")
    vocabulary = _vocabulary(skills_database)
    found, excluded, records = {}, [], []
    sections_seen = set()
    work_entries, internships, projects, certifications = [], [], [], []
    freelance_entries = []
    previous_engagement = None
    previous_section = previous_source = None
    pending_context = None
    previous_number = 0
    raw_lines = text.splitlines()
    limited = False
    for number, section, line in _sections(text, matching_context=matching_context):
        sections_seen.add(section)
        raw_heading = _norm(raw_lines[number - 1].split(":", 1)[0].strip().lstrip("•*- "))
        if section != previous_section or raw_heading in SECTION_ALIASES:
            previous_source = None
            pending_context = None
        elif number != previous_number + 1:
            pending_context = None
        previous_number = number
        source = _source(section, line, previous_source)
        if source != previous_source or (source=='work_experience' and WORK_ROLE.search(line) and not ACTION.search(line)):
            previous_engagement = None
        previous_section, previous_source = section, source
        engagement = ('part_time' if re.search(r'\bpart[- ]time\b',line,re.I) else ('full_time' if re.search(r'\bfull[- ]time|penuh waktu\b',line,re.I) and not NEGATION_CUE.search(line) else None))
        if source == 'freelance':engagement='freelance'
        elif source != 'work_experience':previous_engagement=None
        if engagement:previous_engagement=engagement
        records.append((number, source, line))
        record = {
            "evidence": evidence_excerpt(line), "line": number, "source": source,
            "duration_eligible": bool(asserted_clauses(line)) and pending_context is None,
            "engagement_type": previous_engagement if source in {"work_experience","freelance"} else None,
        }
        target = {"work_experience": work_entries, "internship": internships,
                  "projects": projects, "freelance": freelance_entries, "certifications": certifications}.get(source)
        if target is not None:
            target.append(record)
        for clause in _split_clauses(line):
            claim_source = "projects" if _local_project_claim(clause, source) else source
            if claim_source == "projects" and source != "projects":
                projects.append({"evidence": evidence_excerpt(clause.strip()), "line": number,
                                 "source": "projects", "duration_eligible": False})
            normalized = _norm(clause)
            # PDF wrapping may put a negation/learning cue on the preceding line.
            # A new explicit positive predicate ends that continuation.
            inherited = pending_context if not ACTION.search(clause) else None
            for canonical, variants in vocabulary.items():
                seen_spans = set()
                for variant in sorted(variants, key=lambda value: (-len(value), value)):
                    for match in re.finditer(rf"(?<!\w){re.escape(variant)}(?!\w)", normalized):
                        if match.span() in seen_spans:
                            continue
                        seen_spans.add(match.span())
                        reason = _rejection(normalized, match.start(), match.end(), claim_source)
                        if not reason and inherited:
                            reason = inherited["reason"]
                        if not reason and _domain_context(canonical, normalized, claim_source):
                            reason = "industry_domain_context"
                        if not reason and _ambiguous_skill(canonical, variant, normalized, claim_source):
                            reason = "ambiguous_context"
                        mention = {
                            "name": canonical, "evidence": evidence_excerpt(clause.strip(), match.start(), match.end()),
                            "source": claim_source, "line": number,
                        }
                        if reason:
                            if inherited:
                                mention["context_evidence"] = inherited
                            if len(excluded) < MAX_EXCLUDED_MENTIONS:
                                excluded.append({**mention, "reason": reason})
                            else:
                                limited = True
                            continue
                        mention["skill_kind"] = skill_kind(canonical)
                        mention["claim_status"] = "reported_positive"
                        mention["proficiency"] = "basic" if re.search(
                            rf"(?<!\w){re.escape(variant)}\s+(?:basics?|dasar)(?!\w)", normalized
                        ) else "unspecified"
                        mention["evidence_type"] = {
                            "work_experience": "professional", "internship": "internship",
                            "projects": "project", "freelance": "freelance", "skills": "listed",
                        }.get(claim_source, "mentioned")
                        if canonical not in found:
                            found[canonical] = {**mention, "evidence_items": []}
                        items = found[canonical]["evidence_items"]
                        if mention not in items:
                            if len(items) < MAX_MENTIONS_PER_SKILL:
                                items.append(mention)
                            else:
                                limited = True
            if ACTION.search(clause) and not (NEGATION_CUE.search(clause) or ASPIRATION_CUE.search(clause)):
                pending_context = None
        last_clause = _norm(_split_clauses(line)[-1])
        continuation = re.search(r"(?:\b(?:with|in|of|for|learn|learning|menguasai|menggunakan|mempelajari|belajar|keahlian|expertise|and|or|dan|atau)|[, :])$", last_clause)
        if continuation:
            reason = _rejection(last_clause, len(last_clause), len(last_clause), source)
            if reason:
                pending_context = {"reason": reason, "evidence": evidence_excerpt(line), "line": number}
        elif re.search(r"[.!?]$", line):
            pending_context = None
    education = understand_education(text)
    warnings = []
    if not found:
        warnings.append("Tidak ada skill positif dari vocabulary yang didukung bukti CV.")
    if education["level"] is None:
        warnings.append("Pendidikan belum dapat diverifikasi dari bukti gelar yang tersedia.")
    if not (work_entries or internships or projects):
        warnings.append("Pengalaman/proyek tidak teridentifikasi; durasi profesional tidak diketahui.")
    if limited:
        warnings.append("Metadata bukti dibatasi: maksimal 5 bukti positif per skill dan 1000 mention yang dikecualikan.")
    return {
        "schema_version": "1.1", "engine_version": "ai3b.1",
        "skills": [found[key] for key in sorted(found)],
        "excluded_skill_mentions": excluded,
        "experience": {"professional_years": None, "work_entries": work_entries,
                       "internships": internships, "projects": projects, "freelance_entries": freelance_entries},
        "education": education, "certifications": certifications,
        "quality_warnings": warnings, "sections_detected": sorted(sections_seen - {"unspecified"}),
        "source_policy_version": "local_project_v1",
        "evidence_policy": "Positive CV claims only; absent evidence is not proof of absent ability. Excerpts are capped at 400 characters; long excerpts are normalized.",
    }


def understand_cv_from_file(text: str, skills_db_path: str | Path | None = None) -> dict[str, Any]:
    db_path = Path(skills_db_path) if skills_db_path else Path(__file__).with_name("skills_database.json")
    with db_path.open(encoding="utf-8") as handle:
        return understand_cv(text, json.load(handle))
