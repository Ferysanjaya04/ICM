# Data Flow Diagram — IT Career CV Analyzer & Matchmaking System

Sistem bersifat **dual-mode**: Fitur 1 (CV vs Job Matching, top-down) dan Fitur 2 (Career Recommendation & Blueprint, bottom-up). Keduanya berbagi tahap parsing/ekstraksi yang sama sebelum bercabang ke pipeline AI masing-masing.

---

## DFD Level 0 (Context Diagram)

```mermaid
flowchart LR
    A([Pengguna\nFresh graduate / Junior IT / Career switcher]) -- "cv_file (PDF)\n+ job_file (PDF, opsional untuk Fitur 1)" --> S((0.0\nIT Career CV Analyzer\n& Matchmaking System))
    S -- "Fitur 1: compatibility_score, matched/missing skills, recommendations\nFitur 2: recommended_roles, skill_gap_analysis, learning_path, market_insight" --> A
```

**Entitas luar:** Pengguna (mahasiswa akhir, fresh graduate, junior IT 0–3 tahun, career switcher)
**Sistem:** IT Career CV Analyzer & Matchmaking System
**Data masuk:** `cv_file` (PDF, wajib), `job_file` (PDF, hanya untuk Fitur 1)
**Data keluar:** hasil kompatibilitas CV↔lowongan (Fitur 1) *atau* blueprint karir & rekomendasi role (Fitur 2)

---

## DFD Level 1 (Rincian Proses Utama)

```mermaid
flowchart TD
    A([Pengguna]) -- "Upload PDF\nvia drag-and-drop" --> P1["1.0\nUpload & Validasi\n(FastAPI, Pydantic v2)\ntipe PDF, ≤10 MB"]

    P1 -- "cv_file (+ job_file jika Fitur 1)" --> FS[(File Storage\nSementara)]
    FS -- "File path/bytes" --> P2["2.0\nPDF Parsing & Ekstraksi\n(PyMuPDF, fallback OCR\nTesseract jika teks < 80 char)"]

    P2 -- "Teks mentah per halaman" --> P3["3.0\nSection Detection\n& Entity Extraction\n(rule-based + kamus ID/EN,\nfuzzy skill match, regex identitas)"]

    D1[(skills_database.json\n120+ skill, 11 kategori)] -- "skill dictionary (120+ skills, 11 categories)" --> P3

    P3 -- "Teks tersegmentasi +\nentitas terstruktur (skill, identitas,\npengalaman, pendidikan)" --> P3A["3.1\nLoad AI Models\n(SentenceTransformer +\nTF-IDF/LR .joblib)"]
    P3A --> P4A["4.0\nFitur 1: CV vs Job Matching\n(SentenceTransformer + rule-based)"]
    P3A --> P4B["5.0\nFitur 2: Career Recommendation\n(TF-IDF + Logistic Regression)"]

    D2[(job_roles.csv\n324 role IT)] -- "job requirements (skills, education, experience)" --> P4A
    D2 -- "market data (salary range, category, sector)" --> P4B

    P4A -- "compatibility_score/level,\nmatched/missing skills, recommendations" --> P5["6.0\nPenyimpanan & Generasi Response"]
    P4B -- "top-3 recommended_roles,\nskill_gap_analysis, learning_path,\nmarket_insight" --> P5

    P5 -- "simpan riwayat analisis" --> D3[(PostgreSQL\nhasil analisis & riwayat)]
    P5 -- "JSON response\n(spec docs/api_spec_draft.md)" --> A
```

### Rincian tiap proses

**1.0 — Upload & Validasi**
- Endpoint: `POST /api/v1/match-job` (Fitur 1) atau `POST /api/v1/analyze-cv` (Fitur 2)
- Validasi: tipe file PDF, ukuran ≤ 10 MB (Pydantic v2), file disimpan sementara (*temp storage*)

**2.0 — PDF Parsing & Ekstraksi**
- `PyMuPDF` mengekstrak teks per halaman
- Fallback OCR (`Tesseract`) otomatis dipicu jika teks hasil ekstraksi < 80 karakter (indikasi PDF hasil scan/gambar)

**3.0 — Section Detection & Entity Extraction**
- Segmentasi teks ke 10 section (identitas, ringkasan, keterampilan, pengalaman, pendidikan, proyek, sertifikasi, dll.) berbasis kamus kata kunci Indonesia/Inggris
- Ekstraksi skill via *fuzzy matching* ke `skills_database.json`
- Ekstraksi entitas identitas (nama, email, phone, LinkedIn, GitHub, institusi, perusahaan, periode) via regex + heuristic

**3.1 — Load AI Models**
- Load `SentenceTransformer (all-MiniLM-L6-v2)` dari cache/local untuk embedding semantik
- Load `job_role_classifier.joblib` (TF-IDF Vectorizer + LogisticRegression) untuk klasifikasi role
- Model di-load sekali di *startup* (bukan per request) untuk performa optimal

**4.0 — Fitur 1: CV vs Job Matching** *(hanya jika `job_file` diunggah)*
- Encode CV & JD dengan `SentenceTransformer (all-MiniLM-L6-v2)` → cosine similarity (*semantic_score*)
- Hitung *skill Jaccard* (`skill_score`), *experience rule* (`experience_score`), *education rule* (`education_score`)
- *Weighted sum* → `compatibility_score` & `compatibility_level` (HIGH/MEDIUM/LOW)
- Output tambahan: `matched_skills`, `missing_skills`, `recommendations`

**5.0 — Fitur 2: Career Recommendation**
- `TF-IDF Vectorizer` (fit pada training set) → `LogisticRegression.predict_proba` atas 324 role IT
- Ambil Top-3 role dengan `match_score` tertinggi → lookup `job_roles.csv` untuk gaji & kategori (`market_insight`)
- *Feature importance* (bobot TF-IDF) → *AI reasoning keywords*
- `skill_gap_analysis` = required skills top-role − detected skills → `recommended_learning_path`

**6.0 — Penyimpanan & Generasi Response**
- Simpan riwayat analisis ke PostgreSQL (via SQLAlchemy)
- Susun response JSON sesuai `docs/api_spec_draft.md`, kembalikan ke client (frontend merender *score gauge*, *skill chips*, *radar chart*, *career blueprint* naratif)

### Data store

| Data Store | Isi |
|---|---|
| `skills_database.json` | 120+ skill dalam 11 kategori, dipakai untuk fuzzy skill matching |
| `job_roles.csv` | 324 role IT beserta skill, pendidikan, pengalaman, dan rentang gaji yang dibutuhkan |
| `job_role_classifier.joblib` | TF-IDF Vectorizer + LogisticRegression model (11MB) untuk klasifikasi role IT |
| `sentence_transformer_cache/` | Cached `all-MiniLM-L6-v2` model weights (384-dim embedding) |
| PostgreSQL (hasil analisis & riwayat) | Riwayat CV yang dianalisis per pengguna, skor, dan hasil blueprint karir |
| File storage sementara | File PDF CV/JD yang diunggah, disimpan sementara selama proses parsing |
