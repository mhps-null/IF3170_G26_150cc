# IF3170 Tugas Besar 1 - Local Search

Kelompok **G26 – 150cc**

Repository ini berisi implementasi algoritma *local search* untuk masalah **pengepakan paket ke dalam peti kemas truk** (Mejiro Express). Tujuannya adalah memilih paket dan menentukan posisi serta orientasinya di dalam truk agar **total value paket yang terangkut maksimum**, dengan tetap memenuhi batasan:

- paket tidak keluar dari ruang truk dan tidak saling tumpang tindih,
- total berat tidak melebihi kapasitas truk,
- paket tidak boleh melayang (harus ditopang lantai atau paket lain),
- paket *fragile* tidak boleh menjadi penopang paket lain.

Algoritma yang diimplementasikan:

- **Hill-Climbing** (Steepest Ascent, Sideways Move, Random Restart, Stochastic)
- **Simulated Annealing** (cooling schedule geometrik)
- **Genetic Algorithm**
- **Bonus**: objective function alternatif (memakai atribut `eta` dan `weight`) dan bonus pada bagian GA

## Struktur Repository

```
.
├── docs/        # laporan (PDF)
├── input/       # test case (JSON)
├── output/      # hasil run algoritma (gambar PNG dan summary.json)
├── src/
│   ├── foundation.py      # Package, Truck, State, objective function, validasi, neighbor
│   ├── visualization.py   # Visualisasi 3D state truk dan plot perbandingan eksperimen
│   ├── HC/                # Hill-Climbing (Steepest, Sideways, Restart, Stochastic) & runner
│   ├── SA/                # Simulated Annealing, visualisasi, objective bonus, runner
│   └── GA/                # Genetic Algorithm
└── README.md
```

## Setup

Membutuhkan **Python 3.10+**.

```bash
# 1. Buat dan aktifkan virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell)
# source .venv/bin/activate     # Linux / macOS

# 2. Pasang dependensi
pip install matplotlib
```

## Format Input

File JSON di folder `input/`:

```json
{
  "truck": {"w": 10, "l": 20, "h": 5, "maxCapacity": 500},
  "packages": [
    {"id": "P01", "w": 4, "l": 3, "h": 4, "value": 32, "weight": 9, "is_fragile": false, "eta": 3}
  ]
}
```

## Cara Menjalankan

Program dapat dijalankan dari folder `src/` (rekomendasi) atau langsung dari root repositori.

### Jalankan dari folder `src/` (Rekomendasi)

**Hill-Climbing**

```bash
# Menjalankan semua varian sekaligus (3 runs per varian)
python HC/run_hc.py ../input/<nama_file>.json --variant all --runs 3 --out ../output

# Menjalankan varian tertentu
python HC/run_hc.py ../input/<nama_file>.json --variant steepest --runs 3 --out ../output
python HC/run_hc.py ../input/<nama_file>.json --variant sideways --runs 3 --out ../output
python HC/run_hc.py ../input/<nama_file>.json --variant restart --runs 3 --out ../output
python HC/run_hc.py ../input/<nama_file>.json --variant stochastic --runs 3 --out ../output
```

| Opsi | Default | Keterangan |
|---|---|---|
| `--variant` | `all` | Pilihan varian: `steepest`, `sideways`, `restart`, `stochastic`, atau `all` |
| `--runs` | 3 | Jumlah run / percobaan per varian |
| `--seed` | 42 | Seed acak agar hasil dapat direproduksi |
| `--out` | `../output` | Direktori output untuk menyimpan gambar dan ringkasan |
| `--insert-tries` | 50 | Jumlah percobaan sampling posisi penempatan INSERT per paket luar |
| `--max-sideways` | 50 | Batas sideways move (untuk Sideways Move) |
| `--cumulative` | False | Mode sideways kumulatif (default: consecutive / reset saat nilai naik) |
| `--max-restart` | 3 | Batas restart (untuk Random Restart) |
| `--sample-size` | 15 | Jumlah sampel tetangga per iterasi (untuk Stochastic HC) |
| `--max-no-improve` | 50 | Batas toleransi tanpa perbaikan (untuk Stochastic HC) |
| `--show` | – | Tampilkan jendela plot interaktif |

Hasil tiap varian disimpan di `output/hc_<variant>/`:
- `run<N>_initial_final.png` – visualisasi 3D state awal dan akhir (paket di dalam dan di luar truk, value, berat),
- `objective_vs_iter.png` – nilai objective function per iterasi,
- `summary.json` – ringkasan parameter, durasi, iterasi, nilai awal/akhir, dan snapshot penempatan koordinat paket.
Jika menjalankan `--variant all`, grafik perbandingan nilai akhir antar varian disimpan di `output/hc_comparison/hc_variants_comparison.png`.

**Simulated Annealing**

```bash
python SA/run_sa.py ../input/<nama_file>.json --runs 3 --out ../output
```

| Opsi | Default | Keterangan |
|---|---|---|
| `--runs` | 3 | jumlah run |
| `--t0` | rata-rata value paket | suhu awal |
| `--alpha` | 0.999 | faktor pendinginan (T ← α·T) |
| `--t-min` | 0.1 | suhu minimum (kondisi berhenti) |
| `--max-iter` | 20000 | batas iterasi |
| `--objective` | `base` | `base`, `eta`, atau `light` (objective bonus) |
| `--seed` | 42 | seed acak agar hasil dapat direproduksi |
| `--show` | – | tampilkan jendela plot |

Hasil tiap run disimpan di `output/sa_<objective>/`:

- `run<N>_initial_final.png` – visualisasi 3D state awal dan akhir (paket di dalam dan di luar truk, value, berat),
- `objective_vs_iter.png` – nilai objective function per iterasi,
- `sa_probability.png` – nilai e^(ΔE/T) per iterasi,
- `summary.json` – parameter, durasi, jumlah iterasi, frekuensi *stuck*, serta state awal dan akhir.

**Genetic Algorithm**

```bash
# lengkapi sesuai file masing-masing
python <path_ke_runner> ../input/<nama_file>.json
```

### Alternatif: Jalankan dari Root Proyek

Program juga dapat dijalankan langsung dari root repositori menggunakan modul Python (`-m`):

```bash
# Menjalankan Hill-Climbing dari root:
python -m src.HC.run_hc input/<nama_file>.json --variant all --runs 3 --out output

# Menjalankan Simulated Annealing dari root:
python -m src.SA.run_sa input/<nama_file>.json --runs 3 --out output
```

## Catatan Implementasi Fondasi

Modul `src/foundation.py` memuat representasi objek dasar (`Truck`, `Package`, `PackagePlacement`, `State`), validasi batasan fisik, parsing file input JSON, dan fungsi pembangkitan tetangga (*neighbor generation*):

- **Validasi State** (`State.is_valid`):
  - *Dimensi*: Semua paket berada di dalam ruang kontainer truk ($x+w \le W$, $y+l \le L$, $z+h \le H$).
  - *Kapasitas Berat*: Total berat paket terangkut tidak melampaui `maxCapacity` truk.
  - *Overlap*: Tidak ada dua paket atau lebih yang saling tumpang tindih dalam ruang 3D.
  - *Penopang Fisik*: Paket tidak boleh melayang; setiap paket harus bertumpu pada lantai kontainer ($z=0$) atau tepat di atas permukaan atas paket lain.
  - *Proteksi Fragile*: Paket bertanda `is_fragile = true` tidak boleh menjadi penopang bagi paket lain di atasnya.
- **Operator Tetangga** (`State.generate_neighbors`):
  - **MOVE**: Menggeser posisi paket di dalam truk secara lokal ($\pm$ `max_shift` unit pada koordinat $x$ dan $y$, serta menempatkannya pada tingkat ketinggian $z$ penopang yang valid).
  - **SWAP**: Menukar posisi koordinat dan orientasi antara dua paket.
  - **ROTATE**: Rotasi $90^\circ$ terhadap satu sumbu ($x, y,$ atau $z$). Dari orientasi $(w, l, h)$ hanya menghasilkan 3 kemungkinan orientasi: $(l, w, h)$, $(w, h, l)$, atau $(h, l, w)$.
  - **INSERT**: Menempatkan paket dari luar truk ke dalam kontainer dengan memilih orientasi acak dan posisi $(x, y, z)$ yang bertumpu pada lantai atau paket lain (`support levels`).

## Catatan Implementasi Hill-Climbing

- **Steepest Ascent**: Mengevaluasi kandidat tetangga deterministik (swap, move, rotasi 90°) serta sampling operator INSERT (`insert_tries=50` per paket luar). Memilih tetangga dengan peningkatan nilai tertinggi. Jika tidak ditemukan tetangga yang meningkatkan nilai (termasuk saat daftar tetangga terisi namun bernilai $\le$ state saat ini), algoritma melakukan resampling hingga 3 kali (`max_resamples=3`) untuk mengundi ulang kombinasi penempatan INSERT. Pencarian berhenti jika setelah resampling tidak ditemukan peningkatan, tanpa menjamin optimum lokal terhadap seluruh kemungkinan penempatan.
- **Sideways Move**: Mengizinkan perpindahan ke tetangga bernilai sama (plateau) dengan batasan `max_sideways` (default 50 moves berturut-turut / consecutive). Pencarian langsung berhenti begitu batas tercapai.
- **Random Restart**: Menjalankan Steepest Ascent berkali-kali (`max_restart`) dari state awal acak dan melacak solusi terbaik secara global.
- **Stochastic**: Melakukan sampling tetangga on-the-fly yang seimbang antar jenis aksi (swap, move, rotate, insert) tanpa membangun ribuan kandidat di memori, lalu memilih secara acak salah satu tetangga yang *strictly better*. Metrik `iterations` menghitung jumlah perpindahan sukses. Total batch sampling tidak dicatat secara terpisah.

## Catatan Implementasi Simulated Annealing

- **Maksimasi**: ΔE = objective(neighbor) − objective(current). Move dengan ΔE ≥ 0 selalu diterima, move yang lebih buruk diterima dengan probabilitas e^(ΔE/T).
- **Neighbor**: satu neighbor valid dipilih acak dari move *swap*, *move*, *rotate*, dan *insert* (maksimal 30 percobaan; jika tidak ada yang valid, iterasi dilewati dan suhu tetap turun).
- **Stuck**: iterasi di mana neighbor yang lebih buruk ditolak sehingga SA bertahan di state yang sama. Frekuensinya = jumlah stuck / jumlah iterasi.
- **Objective bonus**: `eta` (value dibobot urgensi 1 + 1/(1+ETA)) dan `light` (value dikurangi penalti berat kecil). Keduanya tidak menambah variabel baru.

## Pembagian Tugas

| Anggota | NIM | Tugas |
|---|---|---|
| Nathan Adhika S | 13524041 | Fondasi (objective function, validasi, neighbor, input parser) dan Hill-Climbing (semua varian) |
| Muhammad Haris P S | 13524053 | Simulated Annealing, visualisasi, dan Bonus 1 (objective function alternatif) |
| M Iqbal Raihan | 13524011 | Genetic Algorithm dan Bonus 3 |
