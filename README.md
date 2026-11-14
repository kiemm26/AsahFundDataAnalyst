# Proyek Analisis Data: E-Commerce Public Dataset

Proyek akhir kelas **Belajar Fundamental Analisis Data** (Dicoding Indonesia).
Analisis dilakukan pada pesanan berstatus `delivered` periode **Januari 2017 - Agustus 2018**.

## Pertanyaan Bisnis
1. Kategori produk apa saja yang menghasilkan total revenue tertinggi dan terendah (10 teratas dan 10 terbawah)?
2. Bagaimana tren jumlah pesanan dan total revenue per bulan, dan pada bulan apa terjadi puncaknya?
3. State mana yang memiliki rata-rata review score terendah dan persentase pesanan terlambat tertinggi?

Analisis lanjutan (tanpa machine learning): RFM Analysis, Geospatial Analysis, dan Binning keterlambatan pengiriman.

## Struktur Direktori
```
submission
├─ dashboard
|     ├─ main_data.csv  # data hasil cleaning (hasil ekspor notebook)
|     └─ dashboard.py
├─ data                 # dataset asli (9 file CSV)
├─ notebook.ipynb
├─ README.md
├─ requirements.txt
└─ url.txt              # tautan dashboard di Streamlit Community Cloud
```

## Setup Environment
Disarankan Python 3.10 atau lebih baru. Jalankan dari folder `submission`:
```
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Menjalankan Dashboard
```
streamlit run dashboard/dashboard.py
```
Dashboard terbuka di `http://localhost:8501`. Filter di sidebar: rentang tanggal, state, jumlah kategori
teratas/terbawah, dan minimum pesanan per state.

## Menjalankan Notebook
Notebook membutuhkan Jupyter tambahan (`pip install notebook`). Buka `notebook.ipynb` dari folder `submission`
(path data bersifat relatif ke `data/`), lalu pilih **Run All**. Sel ekspor di notebook akan menulis ulang
`dashboard/main_data.csv`.

## Deploy ke Streamlit Community Cloud
1. Unggah folder proyek ke repositori GitHub. Folder `data/` boleh tidak ikut karena dashboard hanya memakai
   `dashboard/main_data.csv` (±16 MB).
2. Masuk ke [share.streamlit.io](https://share.streamlit.io), pilih **New app**, lalu pilih repositori dan branch.
3. Isi **Main file path** dengan `dashboard/dashboard.py`, lalu **Deploy**.
4. Salin tautan aplikasi ke `url.txt`.
