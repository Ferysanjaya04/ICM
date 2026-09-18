markdown
IT Career CV Analyzer & Recommendation Engine

> Platform cerdas berbasis AI dan arsitektur backend terpusat untuk menganalisis CV, mencocokkan lowongan kerja (Job Matching), serta merekomendasikan jalur karir IT terbaik bagi pengguna.


Anggota Tim
- Ihsan
- Fery
- Jojo
- Farel


Arsitektur & Fitur Utama
Proyek ini mengintegrasikan teknologi Machine Learning, NLP (*Natural Language Processing), dan arsitektur modern untuk menyelesaikan permasalahan nyata pencari kerja:
1. Fitur 1 - AI Matching & Skill Gap Engine: Menganalisis tingkat kecocokan (Compatibility Score) antara teks CV dan deskripsi lowongan kerja (Job Description) secara semantik menggunakan Sentence Transformers, serta mendeteksi skill apa saja yang masih kurang (skill Gap).
2. Fitur 2 - AI Job Role Classifier (Career Blueprint): Memindai keseluruhan isi CV untuk memprediksi dan membandingkan posisi IT mana yang paling akurat dengan profil kandidat, lengkap dengan analisis mendalam berbasis data dan copywriting naratif yang memotivasi.


Struktur Folder Proyek
Repository ini dikelola dengan struktur direktori standar industri:
text
it-career-cv-analyzer/
│
├── backend/            # Backend API (Centralized architecture, REST API, & AI Engine)
│   ├── app/
│   │   ├── api/        # Endpoint routing
│   │   ├── core/       # Konfigurasi utama
│   │   ├── models/     # Model database & ML model loader
│   │   └── services/   # Logika bisnis & pengolahan AI/NLP
│   └── requirements.txt
│
├── frontend/           # Antarmuka pengguna (Mobile / Web Dashboard)
│
├── data/               # Manajemen Dataset
│   ├── raw/            # Dataset mentah (job_roles.csv, training_data, dll.)
│   ├── processed/      # Model machine learning terlatih (.joblib)
│   └── experiments/    # Notebook eksplorasi data (Jupyter/Colab)
│
├── docs/               # Dokumentasi Proyek
│   └── proposal/       # Proposal dan bab laporan
│
├── .gitignore
└── README.md




Dataset yang Digunakan

* **`job_roles.csv`**: Basis pengetahuan (*knowledge base*) yang berisi referensi posisi pekerjaan IT beserta persyaratan keahlian, jenjang pendidikan, dan kisaran gajinya.
* `resumes_train.jsonl` & `resumes_test.jsonl**`: Dataset latih dan uji untuk model klasifikasi peran karir.

Cara Menjalankan Proyek (Setup Lokal)

1. **Clone repository ini:**
bash
git clone [https://github.com/Ferysanjaya04/it-career-cv-analyzer.git](https://github.com/Ferysanjaya04/it-career-cv-analyzer.git)
cd it-career-cv-analyzer


2. **Instal dependensi backend:**
bash
cd backend
pip install -r requirements.txt




3. **Jalankan eksperimen/model** melalui file notebook yang tersedia di folder `data/experiments/` atau Google Colab.
