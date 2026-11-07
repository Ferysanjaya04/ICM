# ICM — IT Career CV Analyzer & Recommendation Engine

Your Smart Path to an IT Career 

> Platform berbasis **Artificial Intelligence (AI)** yang membantu pengguna menganalisis CV, mengukur kecocokan dengan lowongan pekerjaan, dan menemukan rekomendasi karier IT yang sesuai dengan profil serta keterampilan mereka.

![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-F7DF1E?logo=javascript&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)
![Machine Learning](https://img.shields.io/badge/AI-Machine%20Learning-8B5CF6)

---

## fitur Unggulan

**AI CV & Job Matching**

Menganalisis kecocokan CV dengan deskripsi lowongan kerja menggunakan **SentenceTransformer (`all-MiniLM-L6-v2`)** dan *Cosine Similarity*, dilengkapi compatibility score dan skill gap analysis.

**AI Career Recommendation**

Merekomendasikan **Top 3 karier IT** menggunakan **TF-IDF dan Logistic Regression**, lengkap dengan keterampilan yang terdeteksi dan personalized learning path.

**Resume Management**

Upload dan kelola CV dalam format PDF atau DOCX.

**Dashboard & History**

Autentikasi JWT, dashboard pengguna, serta riwayat analisis dan rekomendasi karier.

---

##  Tech Stack

| Frontend | Backend | Database | AI / ML |
|---|---|---|---|
| HTML, CSS, JavaScript | Python, Django REST Framework | PostgreSQL | SentenceTransformer, TF-IDF, Logistic Regression |

---

## Struktur Proyek

```text
ICM/
├── backend/           # Django REST API & AI Engine
│   ├── accounts/
│   ├── resumes/
│   ├── analysis/
│   ├── recommendations/
│   ├── config/
│   └── lib/
├── frontend/          # HTML, CSS & JavaScript
├── data/              # Dataset & ML Models
├── docs/              # Dokumentasi
├── requirements.txt
└── README.md
```

---

##  Quick Start

**1. Clone Repository**

```bash
git clone https://github.com/Ferysanjaya04/ICM.git
cd ICM
```

**2. Install Dependencies** (Python 3.11)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**3. Jalankan Backend**

Siapkan database PostgreSQL dan konfigurasi Django terlebih dahulu.

```bash
cd backend
python manage.py migrate
python manage.py runserver
```

**4. Jalankan Frontend** (terminal baru, dari root `ICM`)

```bash
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

Buka **http://127.0.0.1:5500/login.html**

---

## Development Team

**Kelompok 12 — Pemrograman Internet II**

- Ihsan Abdillah
- Fery Sanjaya
- Johannes Hutapea
- M. Farel Raditya

---

<p align="center">
  <b>✦ ICM — Discover Your Potential. Build Your IT Career.</b>
</p>

<p align="center">
  Made with 💙 by ICM Development Team · 2026
</p>
