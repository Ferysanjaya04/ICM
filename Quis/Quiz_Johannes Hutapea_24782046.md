# QUIZ
## Interconnecting between Digital Awareness and Application Design

**Nama:** Johannes Hutapea  
**NIM:** 24782046  
**Mata Kuliah:** Internet Programming II

---

# Bagian 1. Identitas dan Topik Proyek Aplikasi

## Nama Aplikasi
**IT Career CV Analyzer & Recommendation Engine (ICM)**

## Deskripsi Singkat dan Tujuan Utama Aplikasi
ICM adalah aplikasi web yang menggunakan AI untuk membantu pengguna memahami apakah CV mereka sudah sesuai dengan pekerjaan IT tertentu dan mencari role IT yang cocok dengan kemampuan yang dimiliki. Masalah yang ingin diselesaikan adalah proses membandingkan CV dengan lowongan dan mencari arah karier yang masih banyak dilakukan secara manual.

ICM memiliki dua fitur utama, yaitu **CV vs Job Matching** untuk membandingkan CV dengan job requirement dan **Career Recommendation** untuk memberikan rekomendasi role IT berdasarkan CV pengguna.

## Target Pengguna Utama
Target pengguna utama adalah **fresh graduate dan pencari kerja di bidang Teknologi Informasi**.

---

# Bagian 2. Resume Modul Digital Awareness

## 1. There’s a whole new world out there!

Di sini dibahas bagaimana teknologi digital mempermudah kegiatan sehari-hari, seperti komunikasi, pembayaran, perbankan, pendidikan, mencari informasi, dan penggunaan GPS. Kita juga diajarkan tentang perubahan dari cara analog ke digital, termasuk perkembangan Web 1.0 ke Web 2.0 yang membuat website lebih interaktif. Pada bagian ini juga dijelaskan Internet of Things (IoT), yaitu benda sehari-hari yang dapat terhubung ke internet dan bertukar data. Selain manfaat teknologi, dibahas juga masalah seperti privasi, keamanan data, penggunaan teknologi berlebihan, dan digital divide.

## 2. You’ll Need Some Basic Tools

Pada bagian ini kita diajarkan dasar penggunaan perangkat digital, mulai dari sistem operasi, perangkat input dan output, sampai cara menghubungkan perangkat menggunakan USB, HDMI, dan Bluetooth. Dijelaskan juga cara mengatur file dan folder supaya lebih rapi dan mudah dicari. Selain itu, kita belajar tentang keamanan perangkat dan akun menggunakan password, PIN, atau biometrik. Password yang dibuat sebaiknya cukup panjang dan tidak menggunakan pola atau informasi pribadi yang mudah ditebak.

## 3. This is how you get around and find what you’re looking for

Dimodul 3 dibahas cara menggunakan browser dan search engine untuk mencari informasi dengan lebih efektif. Kita diajarkan teknik pencarian seperti tanda kutip, tanda minus, `site:`, dan `filetype:` agar hasil pencarian lebih sesuai. Dijelaskan juga bahwa hasil pencarian tidak semuanya bisa dipercaya sehingga perlu melihat sumber dan kemungkinan adanya website berbahaya. Pada bagian ini juga dibahas cookies, copyright, Creative Commons, public domain, dan penggunaan karya atau software sesuai lisensinya. Kita juga diajarkan pentingnya mencatat sumber informasi dari internet.

## 4. It just keeps getting better

Bagian ini dijelaskan perkembangan Artificial Intelligence (AI) dan beberapa kegunaannya, seperti menjawab pertanyaan, menerjemahkan, merangkum, menganalisis, dan mengenali pola. Kita juga diajarkan bahwa hasil AI bisa dipengaruhi oleh data, desain, dan cara penggunaannya sehingga bias tetap bisa muncul. Selain AI, dibahas netiquette atau etika berinternet, seperti menghormati orang lain, menjaga privasi, dan berpikir sebelum membuat posting. Pada tahap ini juga dijelaskan pentingnya bertanggung jawab terhadap digital footprint dan informasi yang dibagikan.

## 5. Even Though It’s Digital, It is Real, With Real Consequences

Di sini dibahas digital persona dan bagaimana aktivitas di internet bisa membentuk identitas digital seseorang. Kita juga diajarkan tentang PII atau data pribadi yang dapat digunakan untuk mengenali seseorang dan pentingnya menjaga informasi tersebut. Dijelaskan bahwa informasi di internet bisa tetap ada, disalin, atau dibagikan kembali walaupun sudah dihapus. Pada bagian ini juga dibahas komunikasi negatif, cyberbullying, anonimitas, phishing, identity theft, catfishing, fraud, serta risiko dari penyalahgunaan informasi pribadi.

## 6. Learn About Anything and Everything

Pada bagian ini kita diajarkan langkah dasar untuk menangani masalah teknis, seperti perangkat tidak menyala, perangkat lambat, koneksi bermasalah, lupa password, aplikasi error, atau file yang tidak bisa dibuka. Dijelaskan beberapa langkah seperti mengecek koneksi, restart, update, reinstall, atau mencari bantuan melalui help dan support. Selain troubleshooting, dibahas juga online learning platform dan berbagai sumber belajar. Pada tahap ini kita dikenalkan dengan skills gap, yaitu kemampuan yang masih kurang dan dapat dikembangkan melalui online course, video, MOOCs, e-book, webinar, workshop, dan forum.

---

# Bagian 3. Hubungan dan Implementasi pada Topik Proyek

## 1. Bagaimana rancangan aplikasi dapat mempermudah tugas sehari-hari pengguna? Apa proses “analog/tradisional” dari topik proyekmu yang berhasil disederhanakan menjadi digital

Menurut saya, proses yang paling terbantu dengan ICM adalah membandingkan CV dengan lowongan kerja. Sebelumnya pengguna harus membaca job requirement satu per satu lalu membandingkannya sendiri dengan CV. Setelah itu pengguna masih harus mencari tahu skill apa yang kurang.

Di ICM, pengguna cukup mengunggah CV dan memasukkan job requirement untuk fitur **CV vs Job Matching**. Sistem kemudian melakukan analisis dan menampilkan Compatibility Score, matched skills, skill gap, serta rekomendasi pengembangan skill. Untuk fitur **Career Recommendation**, pengguna cukup menggunakan CV sebagai input untuk mendapatkan rekomendasi role IT.

## 2. Jika aplikasimu memiliki fitur penyimpanan file atau pendaftaran akun, bagaimana kamu merancang struktur penyimpanan file yang intuitif bagi pengguna awam? Bagaimana kamu membantu pengguna membuat kata sandi yang aman?

Pada ICM, CV adalah salah satu input utama sehingga proses upload dibuat sederhana. Pengguna dapat memilih atau mengunggah file CV dalam format **PDF, JPG, atau PNG** tanpa harus memahami struktur penyimpanan di server.

File dan hasil analisis dikelola oleh backend dan database, sedangkan pengguna cukup melihat data melalui aplikasi. Untuk akun, sistem menggunakan **JWT** sebagai autentikasi. Pengguna juga perlu diarahkan untuk menggunakan password yang cukup panjang dan tidak menggunakan informasi pribadi atau pola sederhana seperti `12345` dan `qwerty`.

## 3. Bagaimana kamu mendesain fitur pencarian (search bar) di dalam aplikasi agar pengguna dapat mencari informasi dengan mudah? Selain itu, sebutkan asset eksternal yang digunakan dalam aplikasi (library, API, gambar, icon). Apakah asset-aset tersebut berlisensi open-source, public domain, atau memiliki hak cipta khusus yang wajib dicantumkan?

Search bar pada ICM dibuat sederhana agar pengguna nanti bisa mencari informasi berdasarkan kata yang mudah dipahami, misalnya nama role, skill, atau data yang tersedia di aplikasi. Jika hasil tidak ditemukan, sistem sebaiknya memberikan pesan yang jelas agar pengguna bisa mencoba kata kunci lain.

Beberapa asset atau library yang digunakan dalam project antara lain:

| Asset / Library | Kegunaan |
|---|---|
| Django | Backend |
| Django REST Framework | REST API |
| React | Frontend |
| Vite | Pengembangan dan build frontend |
| scikit-learn | TF-IDF dan Logistic Regression |
| sentence-transformers | SentenceTransformer |
| PyMuPDF | Ekstraksi teks PDF |
| Tesseract OCR | Membaca CV hasil scan |

Untuk library, model, dataset, icon, atau gambar dari pihak lain, sumber dan aturan lisensinya perlu diperiksa sebelum digunakan. Jadi asset dari internet tidak langsung dianggap bebas digunakan hanya karena bisa ditemukan secara online.

## 4. Jika aplikasimu memiliki fitur interaksi social, bagaimana kamu mencegah pelanggaran etika digital di dalamnya? Jika aplikasi menggunakan fitur pintar berbasis AI, bagaimana kamu memastikan AI tersebut bekerja secara etis dan bertanggung jawab bagi pengguna?

ICM menggunakan AI untuk dua hal, yaitu **membandingkan CV dengan job requirement** dan **memberikan rekomendasi role IT**. Menurutku, hasil AI tidak boleh dianggap sebagai keputusan mutlak. Hasilnya lebih tepat digunakan sebagai bahan pertimbangan pengguna.

Pada fitur CV vs Job Matching, sistem memberikan Compatibility Score dan beberapa bagian penilaian seperti Semantic Score, Skill Score, Experience Score, dan Education Score. Pada Career Recommendation, sistem memberikan rekomendasi role beserta confidence atau probability.

Dengan cara tersebut, pengguna bisa melihat hasil analisis dan tetap menentukan keputusan sendiri. Data yang digunakan untuk model juga perlu diperhatikan karena bias pada data dapat memengaruhi hasil rekomendasi.

## 5. Data pribadi sensitive (PII) apa saja yang dikumpulkan oleh aplikasimu? Bagaimana cara kamu melindungi data tersebut agar tidak bocor atau disalahgunakan? Bagaimana aplikasi meminimalkan Risiko pengguna menjadi korban penipuan siber di platform mu?

CV bisa berisi data pribadi seperti nama, pendidikan, pengalaman kerja, skill, sertifikasi, dan informasi lain yang ditulis oleh pengguna. Karena itu, data tersebut hanya perlu digunakan untuk kebutuhan analisis dan rekomendasi.

Akses terhadap data juga perlu dibatasi agar pengguna hanya dapat melihat data miliknya sendiri. Komunikasi frontend dan backend menggunakan REST API dan pada penggunaan sistem yang memerlukan koneksi aman dapat menggunakan HTTPS.

Untuk mengurangi risiko penyalahgunaan, aplikasi tidak perlu meminta data yang tidak berhubungan dengan fitur, misalnya data keuangan atau informasi sensitif lainnya. Pengguna juga perlu diberi tahu bahwa CV yang diunggah berisi data pribadi sehingga harus berhati-hati terhadap informasi yang dimasukkan.

## 6. Ketika aplikasi mengalami masalah teknis (misalnya kehilangan koneksi internet atau kegagalan memuat data), bagaimana aplikasi mengomunikasikannya kepada pengguna? Tuliskan contoh rancangan pesan error ramah pengguna yang memandu pengguna melakukan troubleshooting mandiri secara mudah.

Ketika terjadi masalah teknis, aplikasi sebaiknya tidak hanya menampilkan tulisan seperti “Error”. Jadi pengguna perlu diberi tahu apa masalahnya dan langkah sederhana yang bisa dibuat.

Contohnya ketika CV gagal diproses:

> **“CV belum berhasil diproses. Pastikan file menggunakan format PDF, JPG, atau PNG dan ukuran file sesuai ketentuan. Coba periksa file lalu unggah kembali.”**

Contoh ketika koneksi ke server bermasalah:

> **“Data belum dapat dimuat karena koneksi ke server sedang terganggu. Periksa koneksi internet Anda, lalu coba kembali.”**

Pesan tersebut membantu pengguna melakukan troubleshooting sendiri sebelum meminta bantuan.
