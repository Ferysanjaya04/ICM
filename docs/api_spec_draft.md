# Rancangan Spesifikasi REST API (Draft Minggu 1)
**Proyek:** IT Career CV Analyzer & Matchmaking System  
**Mata Kuliah:** Internet Programming II  
**Kelompok:** Ihsan (Architect), Fery (AI/Data), Jojo (Backend), Farel (Analyst)  
**Tanggal:** Minggu 1 – Foundation & Setup  

---

## Stack Backend (Rencana)
- **Framework:** FastAPI (Python 3.11)  
- **Validasi Data:** Pydantic v2  
- **PDF Parsing:** PyMuPDF (`fitz`)  
- **AI Engine:** `sentence-transformers/all-MiniLM-L6-v2` (Hugging Face)  
- **Database:** PostgreSQL (produksi) / SQLite (development)  
- **Deployment:** Docker + Cloud (VPS / PaaS)  

---

## Endpoint Feature 1 — CV vs Job Requirement Matching   **VALIDATED (PoC Colab)**

### `POST /api/v1/match-job`
**Content-Type:** `multipart/form-data`  

| Field        | Type | Description |
|--------------|------|-------------|
| `cv_file`    | File (PDF) | Curriculum Vitae kandidat |
| `job_file`   | File (PDF) | Job Requirement / Lowongan pekerjaan |

---

### Response JSON (Contoh Nyata dari PoC Colab)

```json
{
  "status": "success",
  "data": {
    "compatibility_score": 86.88,
    "compatibility_level": "HIGH",
    "scores": {
      "semantic_score": 74.83,
      "skill_score": 86.67,
      "experience_score": 100.0,
      "education_score": 90.0
    },
    "matched_skills": [
      "python",
      "react",
      "docker",
      "aws",
      "django",
      "node.js",
      "postgresql",
      "mongodb",
      "javascript",
      "typescript",
      "git",
      "scrum",
      "agile"
    ],
    "missing_skills": [
      "mysql",
      "nosql"
    ],
    "experience_analysis": {
      "cv_explicit_experience": "Fresh graduate dengan project & internship",
      "required_experience": "2 tahun",
      "status": "Fresh graduate accepted with project/portfolio evidence",
      "date_ranges_detected": [
        "juni 2026 – agustus 2026",
        "januari 2026 – maret 2026",
        "september 2025 – desember 2025",
        "2022 – 2026"
      ]
    },
    "education_analysis": {
      "cv_education_level": 2,
      "required_education_level": 2,
      "cv_field": "rekayasa perangkat lunak",
      "required_field": "teknik informatika",
      "status": "Related education field"
    },
    "recommendations": [
      "Perkuat atau tambahkan pengalaman pada skill: mysql",
      "Perkuat atau tambahkan pengalaman pada skill: nosql"
    ]
  }
}
```

---

### Penjelasan Skor (dari PoC)
| Komponen | Metode | Bobot (Contoh) |
|----------|--------|----------------|
| **Semantic Score** | Cosine similarity embedding (CV vs JD) | 30% |
| **Skill Score** | Jaccard / fuzzy match skill dictionary | 30% |
| **Experience Score** | Rule-based (tahun, fresher vs senior) | 20% |
| **Education Score** | Rule-based (jenjang + bidang studi) | 20% |
| **TOTAL** | Weighted sum | 100% |

> **Catatan:** Bobot akhir akan disepakati Minggu 2 setelah eksperimen lebih lanjut.

---

## Endpoint Feature 2 — Career Recommendation (CV Only)   **DALAM PENGEMBANGAN (Minggu 2)**

### `POST /api/v1/analyze-cv`
**Content-Type:** `multipart/form-data`  

| Field     | Type | Description |
|-----------|------|-------------|
| `cv_file` | File (PDF) | Curriculum Vitae kandidat (tanpa Job Requirement) |

---

### Response JSON — **SPEC TENTATIF** (akan final setelah PoC Minggu 2)

```json
{
  "status": "success",
  "data": {
    "profile_summary": {
      "name": "Kesha Amelia Prasetyo",
      "target_role": "Mobile Developer / Flutter Developer",
      "email": "kesha.amelia@email.com",
      "phone": "+62813-9876-5432",
      "linkedin": "linkedin.com/in/keshaamelia",
      "github": "github.com/keshaamelia",
      "location": "Bandung, Indonesia"
    },
    "dominant_category": "Mobile Development",
    "recommended_roles": [
      {
        "role": "Mobile Developer Android",
        "match_score": 92.5,
        "matched_skills": ["Kotlin", "Android SDK", "Firebase", "REST API"],
        "missing_skills": ["Jetpack Compose", "CI/CD Mobile"]
      },
      {
        "role": "Mobile Developer iOS",
        "match_score": 78.0,
        "matched_skills": ["Swift", "Firebase", "REST API"],
        "missing_skills": ["SwiftUI", "Xcode", "App Store Connect"]
      },
      {
        "role": "Full Stack Developer",
        "match_score": 71.2,
        "matched_skills": ["JavaScript", "React Native", "Firebase", "SQL", "Git"],
        "missing_skills": ["Node.js", "Docker", "Kubernetes"]
      }
    ],
    "detected_skills": {
      "programming": ["Dart", "Kotlin", "Swift", "JavaScript", "SQL"],
      "frameworks": ["Flutter", "React Native", "Firebase", "Provider", "Riverpod", "GetX", "BLoC"],
      "databases": ["SQLite", "PostgreSQL", "MongoDB", "Firebase Firestore"],
      "tools_cloud": ["Git", "CI/CD (GitHub Actions, Codemagic)", "Google Play Console", "Firebase Console"],
      "soft_skills": ["Agile/Scrum", "Problem Solving", "Teamwork"]
    },
    "skill_gap_analysis": {
      "critical_missing": ["Jetpack Compose", "SwiftUI", "Kubernetes"],
      "recommended_learning_path": [
        "Jetpack Compose (Modern Android UI)",
        "CI/CD untuk Mobile (Codemagic / GitHub Actions)",
        "Arsitektur Clean / Modular di Flutter"
      ]
    },
    "education": [
      {
        "institution": "Universitas Bina Cendekia",
        "degree": "S1 Teknik Informatika",
        "period": "2022 – 2026",
        "gpa": "3.80/4.00",
        "thesis": "Implementasi Arsitektur Clean Architecture pada Aplikasi Pemesanan Transportasi Real-Time"
      }
    ],
    "experience": [
      {
        "company": "PT Nusantara Digital Kreatif",
        "role": "Junior Mobile Developer (Internship)",
        "period": "Juli 2025 – September 2025",
        "highlights": [
          "Push notification & UI Flutter",
          "Agile/Scrum rituals"
        ]
      }
    ],
    "projects": [
      {
        "name": "Aplikasi E-Commerce \"BelanjaYuk\"",
        "role": "Mobile Developer",
        "period": "April 2026 – Agustus 2026",
        "tech_stack": ["Flutter", "BLoC", "Midtrans", "Firebase Auth"],
        "description": "Aplikasi e-commerce lintas platform dengan payment gateway Midtrans dan autentikasi Firebase."
      },
      {
        "name": "Aplikasi Manajemen Keuangan 'AturDuit'",
        "role": "Mobile Developer",
        "period": "Oktober 2025 – Januari 2026",
        "tech_stack": ["Flutter", "SQLite", "Cloud Sync"],
        "description": "Aplikasi pencatat keuangan 500+ active users, optimasi render 40%, offline-first dengan SQLite."
      }
    ],
    "certifications": [
      "Dicoding Indonesia: Flutter Developer Expert & Multi-Platform App (2026)",
      "Google Cloud Skills Boost: Associate Android Developer Path (2026)"
    ]
  }
}
```

---

## Rencana Pengembangan Feature 2 (Minggu 2)

| Tahap | Deskripsi | Output |
|-------|-----------|--------|
| **2.1** | **Expand Kamus Skill** — sinkronkan `KAMUS_SKILL` dengan `skills_database.json` (120+ skill, 11 kategori) | Coverage skill ≥ 90% pada CV test |
| **2.2** | **Parser Project & Sertifikasi** — deteksi header "Nama Proyek — Peran", "Nama Sertifikasi — Penerbit — Tahun" | Entri `proyek_1`, `proyek_2`, `sertifikasi_1` terstruktur |
| **2.3** | **Ekstrak Identitas** dari section `unclassified` (nama, target_role, kontak, LinkedIn, GitHub) | Field `profile_summary` terisi otomatis |
| **2.4** | **Role Classifier** — TF-IDF / Embedding similarity vs `job_roles.csv` + `training_data.csv` (10k rows) | `recommended_roles` dengan `match_score` |
| **2.5** | **Gap Analysis & Learning Path** — bandingkan skill kandidat vs skill top-3 role | `skill_gap_analysis` + `recommended_learning_path` |
| **2.6** | **Validasi Kuantitatif** — evaluasi pada `test_resumes.json` (8 CV) + sample `training_data.csv` | Precision / Recall / F1 per role |
| **2.7** | **Finalisasi Spec & Contoh Response** — update file ini dengan data real PoC | `docs/api_spec_draft.md` (Feature 2 validated) |

---

## Error Response Standar (Kedua Endpoint)

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "File harus berformat PDF",
    "details": "Received: image/png"
  }
}
```

| HTTP Code | Kode Error | Keterangan |
|-----------|------------|------------|
| 400 | `INVALID_FILE_TYPE` | Bukan PDF |
| 400 | `EMPTY_PDF_TEXT` | PDF scan tanpa text layer & OCR gagal |
| 413 | `FILE_TOO_LARGE` | > 10 MB |
| 500 | `AI_ENGINE_ERROR` | Gagal inference model |
| 503 | `SERVICE_UNAVAILABLE` | Model loading / maintenance |

---

## Catatan Implementasi (Backend Team - Minggu 5+)

1. **Pre-load Model** saat startup (`lifespan` FastAPI) agar inference cepat.  
2. **Background Task** untuk parsing PDF berat (`BackgroundTasks` atau Celery/Redis nanti).  
3. **Structured Logging** request/response untuk audit & debugging.  
4. **Unit Test** kontrak JSON dengan `pytest` + `httpx` terhadap spec ini.  
5. **OpenAPI Docs** otomatis di `/docs` (Swagger UI) & `/redoc`.

---

## Referensi Dataset & Model
- `job_roles.csv` — 324 peran IT, skill, pendidikan, pengalaman, gaji  
- `skills_database.json` — 120+ skill terkategori (11 kategori)  
- `training_data.csv` — 10.000+ resume berlabel untuk klasifikasi role  
- `test_resumes.json` — 8 CV sintetis untuk validasi akhir  
- Model embedding: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU-friendly)

---

## Versi & History
| Versi | Tanggal | Penulis | Perubahan |
|-------|---------|---------|-----------|
| 0.1   | Minggu 1 | Jojo (Backend) | Draft awal: Feature 1 validated, Feature 2 TBD |
| 0.2   | Minggu 2 | Fery (AI) + Jojo | Update Feature 2 setelah PoC lengkap |

---

> **File ini adalah kontrak desain (Design Contract).**  
> Setiap perubahan breaking-change pada field/structure wajib update versi & diskusi tim terlebih dahulu.