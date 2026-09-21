# Dokumentasi Komponen Backend — IT Career CV Analyzer & Matchmaking System

Ringkasan pustaka (library) dan peran spesifiknya dalam arsitektur: **Client (React SPA) ↔ FastAPI Backend ↔ AI Engine (SentenceTransformer + TF-IDF Classifier) ↔ PostgreSQL + File Storage**.

## Ringkasan

| Komponen | Lapisan | Fungsi Utama |
|---|---|---|
| FastAPI (Python 3.11) | Backend | Framework REST API — orkestrator utama, expose `/api/v1/match-job` & `/api/v1/analyze-cv` |
| Pydantic v2 | Backend | Validasi skema request/response |
| python-multipart | Backend | Parse `multipart/form-data` untuk upload file PDF |
| Uvicorn / Gunicorn | Backend | ASGI server untuk development (Uvicorn) & production (Gunicorn) |
| SQLAlchemy + Alembic | Backend | ORM ke PostgreSQL + migrasi skema database |
| PyMuPDF (fitz) | AI Engine — Parsing | Ekstraksi teks dari file PDF |
| Tesseract (OCR) | AI Engine — Parsing | Fallback OCR saat teks hasil ekstraksi PDF < 80 karakter (PDF scan/gambar) |
| SentenceTransformer (`all-MiniLM-L6-v2`) | AI Engine — Fitur 1 | Embedding semantik 384-dim untuk cosine similarity CV ↔ Job Description |
| Scikit-Learn | AI Engine — Fitur 2 | TF-IDF vectorization + klasifikasi role (Logistic Regression) |
| Pandas | Data | Pengolahan `job_roles.csv` (324 role IT) |
| httpx | Backend | HTTP client untuk integration test endpoint API |
| pytest / pytest-asyncio | Backend | Unit & integration testing |
| ruff / mypy | Backend | Linting & type checking |
| React 18 (TypeScript, Vite) | Frontend | Single Page Application antarmuka pengguna |
| Tailwind CSS | Frontend | Styling |
| React Hook Form | Frontend | Manajemen form upload file |
| Axios | Frontend | HTTP client ke REST API |
| Recharts | Frontend | Visualisasi skor (gauge, radar chart skill) |

## Rincian per komponen

### FastAPI (Python 3.11)
Framework utama REST API, mengorkestrasi dua alur AI berbeda dari satu backend terpusat: **Fitur 1** (`POST /api/v1/match-job`, top-down — CV vs lowongan spesifik) dan **Fitur 2** (`POST /api/v1/analyze-cv`, bottom-up — profil CV tanpa lowongan). Menerima `multipart/form-data`, memvalidasi file (tipe PDF, ≤10 MB), lalu mendelegasikan ke AI Engine.

### Pydantic v2
Mendefinisikan dan memvalidasi skema request (upload file) dan response (mis. `compatibility_score`, `recommended_roles`) sesuai `docs/api_spec_draft.md`, memastikan kontrak API konsisten antara backend dan frontend React.

### python-multipart
Middleware wajib untuk FastAPI guna mem-parse `multipart/form-data` saat upload file PDF (CV & Job Description). Tanpa library ini, FastAPI tidak bisa membaca file dari form upload.

### Uvicorn / Gunicorn
Uvicorn menjalankan server ASGI saat development (auto-reload cepat); Gunicorn (dengan Uvicorn worker) dipakai di production untuk menangani banyak request secara paralel.

### SQLAlchemy + Alembic
SQLAlchemy sebagai ORM untuk membaca/menulis riwayat analisis ke PostgreSQL. Alembic mengelola migrasi skema database seiring perubahan model data (mis. penambahan kolom hasil analisis baru).

### httpx
HTTP client async untuk menulis integration test endpoint API (`/api/v1/match-job`, `/api/v1/analyze-cv`) — mensimulasikan request `multipart/form-data` dan memvalidasi response JSON.

### pytest / pytest-asyncio
Framework unit & integration testing. `pytest-asyncio` mendukung test async FastAPI. Target coverage ≥ 80% untuk pipeline AI & endpoint.

### ruff / mypy
- **ruff**: Linter super cepat (Python), menggantikan flake8 + isort + black — dipakai di CI/CD.
- **mypy**: Static type checker untuk type safety seluruh codebase (Pydantic v2, SQLAlchemy, FastAPI).

### PyMuPDF (fitz)
Tahap pertama pipeline AI — ekstraksi teks berkecepatan tinggi dari file PDF (CV maupun Job Description) per halaman.

### Tesseract (OCR)
Fallback otomatis ketika hasil ekstraksi PyMuPDF menghasilkan teks < 80 karakter (indikasi PDF berupa hasil scan/gambar), agar dokumen non-teks tetap bisa diproses.

### SentenceTransformer (`all-MiniLM-L6-v2`)
Menghasilkan embedding 384-dimensi dari teks CV dan Job Description untuk **Fitur 1**. Cosine similarity antar embedding menjadi `semantic_score`, digabung dengan skor berbasis aturan (skill Jaccard, experience, education) menjadi `compatibility_score` akhir. PoC tervalidasi: compatibility 86.88% (semantic 74.83%, skill 86.67%).

### Scikit-Learn
Pipeline **Fitur 2**: `TfidfVectorizer` mengubah teks CV menjadi vektor numerik, lalu `LogisticRegression` memprediksi probabilitas terhadap 324 role IT (`predict_proba`). Top-3 role dengan probabilitas tertinggi menjadi `recommended_roles`. PoC tervalidasi: accuracy 91.25% pada hold-out set `resumes_test.jsonl`.

### Pandas
Mengolah `job_roles.csv` (324 role IT beserta skill, pendidikan, pengalaman, dan rentang gaji) — dipakai untuk lookup `market_insight` (Fitur 2) dan requirement pembanding (Fitur 1).

### React 18 (TypeScript, Vite) + Tailwind CSS
SPA frontend, dibangun dengan Vite untuk dev server cepat dan TypeScript untuk type-safety. Tailwind CSS untuk styling. Di-deploy statis via Vercel/Netlify.

### React Hook Form, Axios, Recharts
- **React Hook Form** — mengelola state form upload file (drag-and-drop CV/JD PDF) dengan validasi sisi klien.
- **Axios** — mengirim `multipart/form-data` ke endpoint FastAPI dan menangani response JSON.
- **Recharts** — memvisualisasikan hasil: *score gauge* (compatibility_score), *radar chart* kategori skill, chip matched/missing skill.

## Alur integrasi singkat

1. Pengguna upload 1 file (Fitur 2, `/api/v1/analyze-cv`) atau 2 file (Fitur 1, `/api/v1/match-job`) lewat React SPA → dikirim via Axios sebagai `multipart/form-data`.
2. FastAPI (Pydantic v2) memvalidasi tipe & ukuran file, lalu meneruskan ke AI Engine.
3. PyMuPDF mengekstrak teks (fallback Tesseract OCR bila perlu) → section detection & entity extraction (fuzzy match ke `skills_database.json`).
4. Bercabang ke:
   - **Fitur 1**: SentenceTransformer + rule-based scoring → `compatibility_score`, `matched/missing_skills`
   - **Fitur 2**: TF-IDF + Logistic Regression → `recommended_roles`, `skill_gap_analysis`, `market_insight` (lookup `job_roles.csv` via Pandas)
5. Hasil disimpan ke PostgreSQL (SQLAlchemy) sebagai riwayat, lalu dikembalikan sebagai JSON response.
6. React SPA merender hasil dengan Recharts (gauge/radar chart) dan skill chips.
