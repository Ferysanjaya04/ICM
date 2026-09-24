# Laporan Tugas Mandiri / Quiz: Digital Awareness & Application Design

## Bagian 1. Identitas dan Topik Proyek Aplikasi

* **Nama:** Ihsan  
* **NPM:** 24782044  
* **Dosen Pembimbing:**  
  1. Ir. Nurul Qomariyah, S.Kom., M.Kom.  
  2. Ir. Dian Ayu Afifah, S.Si., M.Sc  
* **Kampus:** Politeknik Negeri Lampung  
* **Nama Aplikasi:** ICM (IT Career CV Analyzer & Matchmaking System)  

### Deskripsi Singkat dan Tujuan Utama Aplikasi
ICM adalah platform berbasis web cerdas yang dirancang untuk mengatasi kebingungan mahasiswa tingkat akhir, fresh graduate, maupun pencari kerja pemula di bidang teknologi informasi saat menyusun berkas lamaran dan menentukan arah karier. Permasalahan utama yang dihadapi target pengguna adalah kesulitan menilai apakah keahlian yang tercantum di CV sudah cocok dengan kriteria lowongan industri, minimnya pemahaman mengenai celah kompetensi (*skill gap*), serta tidak adanya gambaran jalur belajar (*learning path*) yang terarah.

Tujuan utama ICM adalah menyediakan evaluasi CV yang objektif, instan, dan terukur melalui dua fungsi utama:
1. **CV vs Job Matching (*Top-Down*):** Mencocokkan CV dengan satu lowongan spesifik untuk menghasilkan skor kompatibilitas (0–100), daftar keterampilan yang cocok maupun yang belum terpenuhi (*matched/missing skills*), serta rekomendasi perbaikan isi CV.
2. **Career Recommendation (*Bottom-Up*):** Memindai profil CV tanpa lowongan tertentu guna merekomendasikan tiga peran IT yang paling sesuai, menganalisis kesenjangan keterampilan, serta menyusun prioritas materi belajar secara bertahap.

### Target Pengguna Utama
Mahasiswa tingkat akhir jurusan rumpun informatika/komputer, lulusan baru (*fresh graduate*) dengan pengalaman 0–3 tahun, serta *career switcher* yang sedang berpindah jalur ke industri teknologi.

---

## Bagian 2. Resume Modul Digital Awareness

### Modul 1: There’s a whole new world out there!
Modul ini menjelaskan transformasi mendasar dari dunia analog ke dunia digital. Peralihan ini bukan sekadar mengganti kertas dengan layar, melainkan mengubah alur kerja agar menjadi lebih cepat, terstruktur, dan efisien. Pada sistem analog, pertukaran data memerlukan kontak fisik atau berkas cetak yang memakan waktu dan rawan tercecer. Sebaliknya, sistem digital memanfaatkan komputasi dan internet untuk mengotomatisasi pekerjaan berulang, menghubungkan orang dari jarak jauh, dan membuka akses pengetahuan tanpa batas geografis.

### Modul 2: You’ll Need Some Basic Tools
Modul kedua menguraikan fondasi perangkat keras, sistem operasi, serta kebiasaan teknis yang benar. Sistem operasi berperan sebagai jembatan yang mengatur seluruh sumber daya perangkat dan berkas. Manajemen berkas dan folder yang rapi sangat penting agar informasi mudah ditemukan dan tidak hilang atau tertimpa secara tidak sengaja. Selain itu, modul ini menekankan pentingnya kata sandi yang kuat (kombinasi panjang, karakter acak, huruf besar-kecil, angka, dan simbol) serta keharusan menghindari kata sandi umum demi mencegah akses ilegal ke akun maupun perangkat.

### Modul 3: This is how you get around and find what you’re looking for
Modul ini membahas cara berselancar di internet menggunakan peramban (*web browser*), teknik penelusuran informasi, dan penghargaan atas hak cipta. Pencarian informasi lokal (di perangkat) berbeda dengan pencarian web; pencarian web membutuhkan kata kunci yang tepat, filter cerdas, dan evaluasi kredibilitas sumber. Modul ini juga membedakan status legal konten: karya berhak cipta (*copyright*) yang dilindungi undang-undang dan tidak boleh diambil tanpa izin atau atribusi, karya *public domain* yang bebas digunakan oleh siapa pun tanpa batasan hak cipta, serta lisensi terbuka (*open-source*) yang mengizinkan pemakaian dan modifikasi sesuai ketentuan lisensi.

### Modul 4: It just keeps getting better
Modul keempat mengulas perkembangan teknologi terkini, terutama kecerdasan buatan (*Artificial Intelligence* / AI) dan dampaknya bagi masyarakat. AI mampu memproses data besar, memprediksi tren, serta memahami teks atau gambar. Namun, AI harus diimbangi dengan etika berinternet (*netiquette*) dan tanggung jawab digital. Interaksi di dunia maya menuntut kesopanan, kesadaran bahwa lawan bicara adalah manusia, verifikasi kebenaran agar tidak menyebarkan berita bohong, serta sikap kritis bahwa output sistem cerdas tetap harus diawasi oleh pertimbangan manusia.

### Modul 5: Even Though It’s Digital, It is Real, With Real Consequences
Aktivitas digital memiliki dampak hukum dan sosial nyata di dunia nyata. Modul ini menyoroti perlindungan data pribadi sensitif (*Personally Identifiable Information* / PII) seperti nama lengkap, NIK, alamat, kontak, dan riwayat hidup yang rentan dimanfaatkan untuk pencurian identitas atau penipuan finansial. Jejak digital bersifat abadi dan sulit dihapus sepenuhnya. Oleh karena itu, pengguna perlu menghindari komunikasi negatif seperti perundungan siber (*cyberbullying*), mewaspadai modus penipuan siber (*phishing, scam, fraud*), serta menjauhi pembajakan perangkat lunak (*software piracy*) demi menjaga integritas moral dan keamanan sistem dari ancaman malware.

### Modul 6: Learn About Anything and Everything
Modul penutup membahas kemampuan pemecahan masalah teknis (*troubleshooting*) secara mandiri dan mengenali kesenjangan keterampilan (*skills gaps*). Ketika perangkat atau aplikasi bermasalah, langkah penanganan dimulai dari hal paling sederhana: memeriksa koneksi, meneliti pesan galat, memastikan letak berkas, hingga memperbarui perangkat lunak. Modul ini juga mengajak pembelajar untuk sadar akan kemampuan diri, aktif mencari sumber belajar daring (kursus, dokumentasi resmi, komunitas), dan terus memperbarui keahlian agar relevan dengan kebutuhan zaman.

---

## Bagian 3. Hubungan dan Implementasi pada Topik Proyek

### 1. Kemudahan Pengguna dan Penyederhanaan Proses Analog ke Digital
Dalam alur tradisional/analog, seorang lulusan baru harus mencetak berlembar-lembar CV fisik, membawa map berkas ke bursa kerja (*job fair*), atau mengirimkan lamaran ke puluhan instansi secara acak tanpa mengetahui apakah kualifikasinya sesuai. Proses verifikasi kesesuaian ini biasanya membutuhkan waktu berhari-hari hingga berminggu-minggu secara manual oleh pihak pelamar maupun perekrut, dan pelamar sering kali tidak pernah mendapat alasan mengapa berkasnya ditolak.

Aplikasi ICM menyederhanakan proses tersebut menjadi sistem digital terpadu:
* Pelamar cukup mengunggah satu berkas digital CV (format PDF).
* Dalam waktu kurang dari 3 detik, sistem melakukan ekstraksi teks otomatis, memetakan keterampilan teknis, dan menghitung kecocokan dengan standar kualifikasi industri.
* Pelamar langsung memperoleh umpan balik transparan berupa persentase skor kecocokan, rincian keahlian yang belum dimiliki, serta rekomendasi materi yang perlu dipelajari. Proses tebak-tebakan dan seleksi buta yang memakan waktu berminggu-minggu disederhanakan menjadi evaluasi instan yang terarah.

### 2. Struktur Penyimpanan Berkas Intuitif dan Keamanan Kata Sandi
* **Penyimpanan Berkas yang Intuitif:**  
  Bagi pengguna awam, ICM menyederhanakan antarmuka unggah menggunakan mekanisme seret-dan-lepas (*drag-and-drop*) dengan indikator status yang jelas (ikon berkas berhasil diunggah, ukuran berkas, dan tombol hapus/ganti). Di sisi server, berkas tidak dibiarkan menumpuk secara berantakan; berkas dipisahkan per sesi pengguna menggunakan folder terisolasi yang dinamai berdasarkan ID acak unik (UUID). Berkas CV sementara segera dibersihkan dari penyimpanan setelah proses analisis teks selesai agar tidak membebani ruang penyimpanan dan menjaga privasi pengguna.
* **Membantu Pengguna Membuat Kata Sandi yang Aman:**  
  Pada formulir pendaftaran, sistem menyediakan pengukur kekuatan kata sandi visual (*visual password strength meter*) secara langsung saat pengguna mengetik. Sistem menerapkan validasi ketat: minimal 8 karakter dengan perpaduan huruf kapital, huruf kecil, angka, dan simbol. Jika kata sandi terlalu lemah (misalnya "123456" atau kata umum), sistem menampilkan instruksi edukatif yang ramah tentang karakter apa yang masih kurang. Di sisi backend, kata sandi pengguna tidak pernah disimpan dalam bentuk teks biasa (*plaintext*), melainkan di-hash satu arah menggunakan algoritma `bcrypt` dengan *salt*.

### 3. Desain Fitur Pencarian (Search Bar) dan Inventaris Aset Eksternal
* **Desain Fitur Pencarian:**  
  Fitur pencarian di dalam ICM dirancang responsif dan toleran terhadap kesalahan ketik (*fuzzy matching* / autocomplete). Saat pengguna mencari posisi pekerjaan atau nama keahlian (misalnya "React", "Python", atau "Data Analyst"), sistem langsung mencocokkan kata kunci tersebut ke dalam basis data pengetahuan internal `skills_database.json` (memuat lebih dari 120 keahlian) dan katalog `job_roles.csv`. Kolom pencarian diletakkan secara strategis di bagian atas dengan ikon kaca pembesar yang universal, teks petunjuk (*placeholder*) yang informatif, serta tombol reset cepat.
* **Aset Eksternal dan Status Lisensi:**  
  Aplikasi ICM dibangun sepenuhnya menggunakan komponen terbuka untuk menjamin legalitas hukum dan kebebasan modifikasi akademik:
  1. *Backend Framework:* **FastAPI** — Berlisensi **MIT License** (Open-source, bebas digunakan dan dimodifikasi).
  2. *Machine Learning & NLP:* **scikit-learn** — Berlisensi **BSD 3-Clause License**; **SentenceTransformer (`all-MiniLM-L6-v2`)** — Berlisensi **Apache License 2.0**.
  3. *Frontend UI & Library:* **React**, **Tailwind CSS**, **Axios**, **Recharts** — Semuanya berlisensi **MIT License**.
  4. *Parsing Dokumen:* **PyMuPDF** — Berlisensi **GNU AGPL / Komersial**; digunakan sesuai batasan open-source non-komersial untuk riset pendidikan.
  5. *Tipografi & Ikon:* Font **Inter** (berlisensi **SIL Open Font License 1.1**) dan paket ikon **Lucide React** (berlisensi **MIT License**).  
  Seluruh pustaka dan aset di atas berstatus open-source legal dan tidak ada aset bajakan (*pirated*) maupun aset berhak cipta khusus yang dilanggar.

### 4. Etika Digital dan Penerapan Kecerdasan Buatan (AI) yang Bertanggung Jawab
* **Pencegahan Pelanggaran Etika:**  
  Aplikasi ICM difokuskan sebagai alat bantu produktivitas individu dan tidak menyediakan fitur interaksi sosial publik (seperti kolom komentar terbuka atau forum percakapan bebas antar pengguna). Keputusan desain ini sengaja diambil untuk meminimalkan potensi perundungan siber (*cyberbullying*), ujaran kebencian, pelecehan, maupun penyebaran konten tidak pantas di dalam platform.
* **Penerapan AI yang Etis dan Bertanggung Jawab:**  
  Model AI yang digunakan (SentenceTransformer untuk kesamaan semantik dan Logistic Regression untuk klasifikasi peran) memiliki tingkat akurasi tinggi pada pengujian (86.88% kompatibilitas dan 91.25% akurasi rekomendasi peran). Namun, pengembang menyadari model AI berpotensi mengalami bias terhadap istilah tertentu. Oleh karena itu, ICM menerapkan prinsip AI yang bertanggung jawab:
  - *Transparansi:* Sistem menampilkan bobot faktor penilaian secara terbuka (persentase keahlian, pengalaman, dan latar belakang pendidikan).
  - *Disclaimer Jelas:* Pada halaman hasil analisis, tercantum catatan bahwa skor dan saran yang diberikan bersifat rekomendasi pendukung keputusan (*decision support*), bukan penentu mutlak kelulusan seleksi kerja.
  - *Kemandirian Pengguna:* AI tidak mengambil tindakan otomatis yang merugikan pengguna, melainkan memposisikan diri sebagai konsultan digital bagi kemajuan karier pengguna.

### 5. Perlindungan Data Pribadi Sensitif (PII) dan Mitigasi Penipuan Siber
* **Identifikasi Data Pribadi Sensitif (PII):**  
  Dokumen CV yang diunggah pengguna memuat data PII yang sangat rentan, antara lain: nama lengkap, alamat tempat tinggal, alamat email, nomor telepon/WhatsApp, tautan profil pribadi (LinkedIn, GitHub, portofolio), riwayat pendidikan, serta riwayat pekerjaan/magang terdahulu.
* **Mekanisme Perlindungan Data:**  
  1. *Penyimpanan Minimal (*Data Minimization*):* Sistem hanya mengekstrak data atribut keahlian dan riwayat relevan ke dalam memori kerja. Berkas fisik PDF langsung dihapus dari direktori penyimpanan sementara (*temporary storage*) setelah analisis selesai.
  2. *Enkripsi dan Akses Terbatas:* Basis data hasil analisis diamankan dengan enkripsi saat transmisi data (HTTPS/TLS) maupun saat disimpan (*at rest*). Kunci akses basis data dikelola terpusat lewat berkas konfigurasi lingkungan terisolasi (`.env`).
  3. *Peniadaan Data Finansial:* ICM sama sekali tidak meminta maupun menyimpan nomor rekening, informasi kartu kredit, atau data keuangan apa pun.
* **Mitigasi Risiko Penipuan Siber:**  
  Untuk melindungi pengguna dari penipuan lowongan kerja palsu (*job scam / phishing*), aplikasi tidak menampilkan data kontak pribadi pelamar secara terbuka di halaman publik yang bisa di-*scrape* oleh pihak ketiga jahat. Jika pengguna memanfaatkan fitur pencocokan terhadap deskripsi lowongan, sistem memvalidasi teks lowongan tersebut untuk mendeteksi ketiadaan kontak resmi perusahaan atau indikasi permintaan pungutan biaya.

### 6. Komunikasi Masalah Teknis dan Rancangan Pesan Galat yang Ramah Pengguna
Ketika sistem mengalami kendala operasional (kegagalan jaringan, berkas rusak, atau kelebihan beban server), aplikasi menghindari tampilan kode status teknis mentah (seperti *Error 500: Internal Server Error* atau *SyntaxError: unexpected token*) yang membingungkan orang awam. Sistem merancang antarmuka status interaktif yang ramah, menenangkan, dan memberikan langkah solusi konkret.

**Contoh Rancangan Pesan Galat Ramah Pengguna:**

1. **Kasus Berkas PDF Tidak Terbaca / Berkas Rusak:**
   > 📄 **Berkas CV Belum Dapat Dibaca**  
   > Sistem kami mengalami kendala saat membaca teks pada berkas yang kamu unggah. Hal ini biasanya terjadi jika berkas berupa hasil scan gambar/foto murni atau berkas terkunci kata sandi.  
   > **Langkah yang dapat kamu lakukan:**  
   > 1. Pastikan berkas tersimpan dalam format PDF berbasis teks (bisa disorot/dicopy).  
   > 2. Pastikan ukuran berkas tidak melebihi batas maksimal 10 MB.  
   > 3. Coba simpan ulang (*Export to PDF*) dokumen CV-mu, lalu unggah kembali.  
   > `[ Tombol: Unggah Ulang Berkas ]`

2. **Kasus Kehilangan Koneksi Internet saat Unggah:**
   > 🌐 **Koneksi Internet Terputus**  
   > Kami tidak dapat menghubungi server karena koneksi internet di perangkatmu terputus saat proses pengiriman berkas.  
   > **Langkah yang dapat kamu lakukan:**  
   > 1. Periksa sambungan Wi-Fi atau paket data selulermu.  
   > 2. Jika koneksi sudah stabil, klik tombol di bawah untuk mengirim ulang tanpa perlu memilih berkas dari awal.  
   > `[ Tombol: Coba Kirim Ulang ]`

3. **Kasus Server Sedang Mengalami Antrean / Pemeliharaan:**
   > ⏳ **Layanan Sedang Mengantre**  
   > Mesin analisis cerdas kami sedang memproses banyak permintaan secara bersamaan.  
   > **Langkah yang dapat kamu lakukan:**  
   > Tunggu sekitar 1 hingga 2 menit, lalu segarkan halaman ini. Data yang telah kamu masukkan tetap aman.  
   > `[ Tombol: Muat Ulang Halaman ]`
