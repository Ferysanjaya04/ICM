# Rancangan Spesifikasi REST API

## IT Career CV Analyzer & Matchmaking System (ICM)

**Mata Kuliah:** Internet Programming II\
**Kelompok:** Ihsan (Architect), Fery (AI/Data), Jojo (Backend), Farel
(Analyst/QA)\
**Backend:** Django 5.x + Django REST Framework\
**Database:** PostgreSQL\
**Authentication:** JWT (SimpleJWT)\
**Status:** Draft / Design Contract

------------------------------------------------------------------------

## 1. Tujuan API

REST API digunakan sebagai penghubung antara frontend dengan backend
ICM. Backend menangani:

1.  autentikasi pengguna;
2.  upload dan pemrosesan CV;
3.  analisis kecocokan CV dengan lowongan;
4.  rekomendasi career/IT role;
5.  penyimpanan hasil analisis pada PostgreSQL.

Arsitektur utama:

``` text
React Frontend
      |
      | HTTP/JSON + multipart/form-data
      v
Django 5 + Django REST Framework
      |
      +---- Authentication / JWT
      |
      +---- CV Processing
      |
      +---- AI Engine
      |       +-- Feature 1: CV vs Job Matching
      |       +-- Feature 2: Career Recommendation
      |
      v
PostgreSQL
```

**Catatan:** REST API adalah gaya/arsitektur komunikasi. Implementasi
API proyek ini menggunakan Django REST Framework, bukan FastAPI.

------------------------------------------------------------------------

# 2. Stack Backend

  Komponen         Teknologi
  ---------------- ----------------------------------------
  Framework        Django 5.x
  REST API         Django REST Framework
  Bahasa           Python 3.11+
  Authentication   SimpleJWT
  Database         PostgreSQL
  PDF Processing   PyMuPDF (`fitz`)
  OCR              Tesseract OCR
  AI Feature 1     SentenceTransformer `all-MiniLM-L6-v2`
  AI Feature 2     TF-IDF + Logistic Regression
  API Format       JSON
  File Upload      `multipart/form-data`
  Testing          pytest + pytest-django
  Deployment       Gunicorn + Nginx / cloud

------------------------------------------------------------------------

# 3. Standar Response API

## 3.1 Success Response

Seluruh endpoint menggunakan struktur:

``` json
{
  "status": "success",
  "data": {}
}
```

Contoh:

``` json
{
  "status": "success",
  "data": {
    "message": "Registrasi berhasil.",
    "user": {
      "id": 1,
      "username": "jojo",
      "email": "jojo@example.com"
    }
  }
}
```

## 3.2 Error Response

``` json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "username, email, dan password wajib diisi.",
    "details": null
  }
}
```

------------------------------------------------------------------------

# 4. Authentication API

Authentication merupakan bagian backend foundation dan sudah
diimplementasikan pada M5.

## 4.1 Register

### `POST /api/auth/register/`

**Content-Type:** `application/json`

### Request

``` json
{
  "username": "jojo",
  "email": "jojo@example.com",
  "password": "Password123!"
}
```

### Response --- 201 Created

``` json
{
  "status": "success",
  "data": {
    "message": "Registrasi berhasil.",
    "user": {
      "id": 1,
      "username": "jojo",
      "email": "jojo@example.com"
    }
  }
}
```

### Error

Username sudah digunakan:

``` json
{
  "status": "error",
  "error": {
    "code": "USERNAME_ALREADY_EXISTS",
    "message": "Username sudah digunakan.",
    "details": null
  }
}
```

Email sudah digunakan:

``` json
{
  "status": "error",
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "Email sudah digunakan.",
    "details": null
  }
}
```

------------------------------------------------------------------------

## 4.2 Login

### `POST /api/auth/login/`

**Content-Type:** `application/json`

### Request

``` json
{
  "username": "jojo",
  "password": "Password123!"
}
```

### Response --- 200 OK

``` json
{
  "status": "success",
  "data": {
    "refresh": "<JWT_REFRESH_TOKEN>",
    "access": "<JWT_ACCESS_TOKEN>"
  }
}
```

### Error --- 401 Unauthorized

``` json
{
  "status": "error",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Username atau password salah.",
    "details": null
  }
}
```

------------------------------------------------------------------------

## 4.3 Current User

### `GET /api/auth/me/`

**Authentication:** Bearer JWT

### Header

``` text
Authorization: Bearer <ACCESS_TOKEN>
```

### Response --- 200 OK

``` json
{
  "status": "success",
  "data": {
    "id": 1,
    "username": "jojo",
    "email": "jojo@example.com"
  }
}
```

------------------------------------------------------------------------

# 5. Resume API

## 5.1 Upload CV

### `POST /api/resumes/upload/`

**Authentication:** Bearer JWT\
**Content-Type:** `multipart/form-data`

### Request

  Field                 Type     Keterangan
  --------------------- -------- ---------------------------------
  `cv_file`             File     File CV kandidat
  `original_filename`   String   Nama file asli, bila diperlukan

Format yang direncanakan:

-   PDF
-   JPG
-   PNG

Batas ukuran file: **10 MB**.

### Response --- Rencana

``` json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "original_filename": "cv_jojo.pdf",
    "message": "CV berhasil diupload."
  }
}
```

**Status:** Endpoint dikembangkan pada tahap CV Processing. Kontrak
dapat disesuaikan ketika implementasi final dibuat.

------------------------------------------------------------------------

# 6. Feature 1 --- CV vs Job Requirement Matching

Feature 1 membandingkan CV kandidat dengan Job Requirement menggunakan
beberapa komponen:

-   semantic similarity;
-   skill matching;
-   experience analysis;
-   education analysis.

Model semantic menggunakan:

`sentence-transformers/all-MiniLM-L6-v2`

Embedding berdimensi 384.

## 6.1 Endpoint

### `POST /api/analyze/cv-match/`

**Authentication:** Bearer JWT\
**Content-Type:** `multipart/form-data`

### Request

  Field         Type     Keterangan
  ------------- -------- -------------------------------------------
  `resume_id`   UUID     ID CV yang sudah diupload
  `job_file`    File     Job Requirement
  `job_text`    String   Alternatif Job Requirement berbentuk teks

Implementasi final dapat menggunakan `resume_id` + `job_file` agar CV
tidak perlu dikirim berulang kali.

------------------------------------------------------------------------

## 6.2 Response

``` json
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
      "status": "Fresh graduate accepted with project/portfolio evidence"
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

## 6.3 Komponen Scoring

Bobot final mengikuti hasil validasi AI yang digunakan pada laporan
proyek. Jika bobot mengalami perubahan setelah eksperimen, dokumentasi
harus diperbarui.

  Komponen              Metode
  --------------------- -----------------------------
  Semantic Score        Cosine similarity embedding
  Skill Score           Skill matching
  Experience Score      Rule-based analysis
  Education Score       Rule-based analysis
  Compatibility Score   Weighted sum

**Catatan:** Compatibility Score adalah nilai kecocokan CV terhadap job
requirement, bukan akurasi model.

------------------------------------------------------------------------

# 7. Feature 2 --- Career Recommendation

Feature 2 menganalisis CV tanpa membutuhkan Job Requirement tertentu.

AI digunakan untuk menentukan rekomendasi role IT berdasarkan isi CV.

Metode utama:

-   TF-IDF;
-   Logistic Regression;
-   top-3 role recommendation;
-   skill gap analysis.

## 7.1 Endpoint

### `POST /api/recommend/career/`

**Authentication:** Bearer JWT\
**Content-Type:** `multipart/form-data`

### Request

  Field         Type   Keterangan
  ------------- ------ -----------------------
  `resume_id`   UUID   ID CV yang dianalisis

------------------------------------------------------------------------

## 7.2 Response

Struktur final akan mengikuti hasil implementasi Feature 2.

Contoh:

``` json
{
  "status": "success",
  "data": {
    "dominant_category": "Software Development",
    "profile_summary": {},
    "detected_skills": {},
    "top_roles": [
      {
        "rank": 1,
        "role_title": "Full Stack Developer",
        "match_percentage": 92.50,
        "category": "Software Development",
        "salary_range": "Rp ..."
      },
      {
        "rank": 2,
        "role_title": "Backend Developer",
        "match_percentage": 87.20,
        "category": "Software Development",
        "salary_range": "Rp ..."
      },
      {
        "rank": 3,
        "role_title": "DevOps Engineer",
        "match_percentage": 79.40,
        "category": "DevOps",
        "salary_range": "Rp ..."
      }
    ],
    "learning_path": {}
  }
}
```

**Catatan:** `match_percentage` merupakan nilai rekomendasi/kecocokan
role, bukan probabilitas seseorang akan diterima kerja.

------------------------------------------------------------------------

# 8. History API

## 8.1 Analysis History

### `GET /api/results/history/`

**Authentication:** Bearer JWT

Endpoint digunakan untuk mengambil riwayat analisis milik user yang
sedang login.

Contoh response:

``` json
{
  "status": "success",
  "data": {
    "results": []
  }
}
```

------------------------------------------------------------------------

## 8.2 Detail Analysis

### `GET /api/results/<id>/`

**Authentication:** Bearer JWT

Digunakan untuk mengambil detail satu hasil analisis berdasarkan ID.

------------------------------------------------------------------------

# 9. Database Model

Backend menggunakan PostgreSQL.

Model utama:

``` text
User
 │
 ├── Resume
 │     │
 │     └── JobMatch
 │
 └── CareerRecommendation
         │
         └── TopRole

JobRole
```

### Resume

Menyimpan:

-   user;
-   file CV;
-   nama file;
-   extracted text;
-   parsed sections;
-   waktu upload.

### JobMatch

Menyimpan:

-   user;
-   resume;
-   job requirement;
-   compatibility score;
-   semantic score;
-   skill score;
-   experience score;
-   education score;
-   matched skills;
-   missing skills;
-   recommendations.

### CareerRecommendation

Menyimpan:

-   user;
-   resume;
-   dominant category;
-   profile summary;
-   detected skills;
-   learning path.

### TopRole

Menyimpan:

-   recommendation;
-   role title;
-   match percentage;
-   rank;
-   salary range;
-   category.

### JobRole

Menyimpan database role IT:

-   role title;
-   category;
-   description;
-   required skills;
-   salary range.

------------------------------------------------------------------------

# 10. Error Response

Standar error API:

``` json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Penjelasan error.",
    "details": null
  }
}
```

Error yang direncanakan:

    HTTP Kode                      Keterangan
  ------ ------------------------- ----------------------------------
     400 `VALIDATION_ERROR`        Input tidak valid
     400 `INVALID_FILE_TYPE`       Format file tidak didukung
     400 `EMPTY_PDF_TEXT`          Teks CV tidak berhasil diekstrak
     401 `AUTHENTICATION_FAILED`   Login gagal / token tidak valid
     403 `PERMISSION_DENIED`       User tidak memiliki akses
     404 `NOT_FOUND`               Resource tidak ditemukan
     413 `FILE_TOO_LARGE`          File \> 10 MB
     500 `AI_ENGINE_ERROR`         Gagal menjalankan AI engine
     503 `SERVICE_UNAVAILABLE`     Service/model tidak tersedia

------------------------------------------------------------------------

# 11. Testing

Automated testing menggunakan:

-   pytest;
-   pytest-django;
-   Django REST Framework APIClient.

Authentication telah divalidasi dengan 5 test:

1.  Register berhasil;
2.  Register dengan username duplikat;
3.  Login berhasil;
4.  Login dengan password salah;
5.  Akses `/api/auth/me/` menggunakan JWT.

Status pengujian M5:

``` text
5 passed
```

Test selanjutnya akan ditambahkan untuk:

-   CV upload;
-   file validation;
-   Feature 1;
-   Feature 2;
-   authorization;
-   result history.

------------------------------------------------------------------------

# 12. Alur Request Feature 1

``` text
Client
  |
  | POST /api/analyze/cv-match/
  | resume_id + job_file
  v
Django REST Framework
  |
  +--> Authentication / JWT
  |
  +--> Validasi request & file
  |
  +--> Ambil Resume
  |
  +--> Extract / normalize text
  |
  +--> AI Engine
  |      |
  |      +--> SentenceTransformer
  |      +--> Semantic Score
  |      +--> Skill Matching
  |      +--> Experience Analysis
  |      +--> Education Analysis
  |      +--> Compatibility Score
  |
  +--> Simpan JobMatch
  |
  v
JSON Response
  |
  v
Client / React Dashboard
```

------------------------------------------------------------------------

# 13. Alur Request Feature 2

``` text
Client
  |
  | POST /api/recommend/career/
  | resume_id
  v
Django REST Framework
  |
  +--> Authentication / JWT
  |
  +--> Ambil Resume
  |
  +--> Extract / normalize text
  |
  +--> AI Engine
  |      |
  |      +--> TF-IDF
  |      +--> Logistic Regression
  |      +--> Top-3 Role
  |      +--> Skill Gap
  |      +--> Learning Path
  |
  +--> Simpan CareerRecommendation
  |
  v
JSON Response
  |
  v
Client / React Dashboard
```

------------------------------------------------------------------------

# 14. Keamanan API

Implementasi backend menggunakan:

-   JWT authentication;
-   password hashing bawaan Django;
-   permission `IsAuthenticated` untuk endpoint yang membutuhkan user;
-   validasi input;
-   validasi tipe dan ukuran file;
-   pembatasan akses data berdasarkan user.

Token tidak disimpan sebagai password atau data plaintext pada database.

------------------------------------------------------------------------

# 15. Referensi Dataset & Model

-   `job_roles.csv` --- database role IT;
-   `skills_database.json` --- kamus skill;
-   `training_data.csv` --- dataset training role classifier;
-   `test_resumes.json` --- data validasi;
-   `sentence-transformers/all-MiniLM-L6-v2` --- model embedding Feature
    1.

Detail jumlah data, metrik evaluasi, dan hasil eksperimen mengikuti
laporan AI/PoC tim dan dapat diperbarui setelah validasi final.

------------------------------------------------------------------------

# 16. Status Pengembangan

  Komponen                           Status
  ---------------------------------- ----------------------
  Django 5.x + virtual environment   Selesai
  PostgreSQL                         Selesai
  Database models                    Selesai
  Migrations                         Selesai
  JWT Register                       Selesai
  JWT Login                          Selesai
  `/api/auth/me/`                    Selesai
  Standard success response          Selesai
  Standard error response            Selesai
  Automated authentication test      Selesai --- 5 passed
  Resume upload                      Tahap pengembangan
  CV Processing / OCR                Tahap pengembangan
  Feature 1                          Tahap pengembangan
  Feature 2                          Tahap pengembangan
  Frontend integration               Tahap berikutnya
  Deployment                         Tahap akhir

------------------------------------------------------------------------

# 17. Versi & History

  -----------------------------------------------------------------------
  Versi             Tahap             Penulis           Perubahan
  ----------------- ----------------- ----------------- -----------------
  0.1               Minggu 1          Jojo              Draft REST API

  0.2               Minggu 2          Fery + Jojo       PoC AI Feature
                                                        1/2

  0.3               M5                Jojo              Sinkronisasi API
                                                        dengan Django +
                                                        DRF, JWT,
                                                        PostgreSQL,
                                                        response schema,
                                                        dan automated
                                                        testing
  -----------------------------------------------------------------------

------------------------------------------------------------------------

> **Design Contract**
>
> Dokumen ini menjadi acuan kontrak REST API antara frontend, backend,
> dan AI engine.
>
> Perubahan yang mengubah nama endpoint, field, tipe data, atau struktur
> response secara breaking-change harus diperbarui pada dokumen ini dan
> dikomunikasikan kepada anggota tim terkait.
