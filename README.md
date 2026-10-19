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
source .venv/bin/activate     # Linux / macOS

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

**Jalankan semua perintah dari root repository**

Gunakan `input/sample_input.json` sebagai contoh input; ganti dengan path JSON lain jika diperlukan.

### Hill-Climbing

```bash
# Jalankan semua varian, 3 run per varian
python -m src.HC.run_hc input/sample_input.json --variant all --runs 3 --out output

# Jalankan satu varian tertentu
python -m src.HC.run_hc input/sample_input.json --variant steepest --runs 3 --out output
python -m src.HC.run_hc input/sample_input.json --variant sideways --runs 3 --out output
python -m src.HC.run_hc input/sample_input.json --variant restart --runs 3 --out output
python -m src.HC.run_hc input/sample_input.json --variant stochastic --runs 3 --out output
```

| Opsi | Default | Keterangan |
|---|---|---|
| `--variant` | `all` | Varian: `steepest`, `sideways`, `restart`, `stochastic`, atau `all` |
| `--runs` | 3 | Jumlah run per varian |
| `--seed` | 42 | Seed awal agar eksperimen dapat direproduksi |
| `--out` | `./output` | Direktori dasar output |
| `--insert-tries` | 50 | Jumlah percobaan sampling posisi INSERT per paket di luar truk |
| `--max-sideways` | 50 | Batas sideways move untuk varian `sideways` |
| `--cumulative` | tidak aktif | Jika diaktifkan, sideways move dihitung kumulatif, bukan hanya berturut-turut |
| `--max-restart` | 3 | Jumlah restart untuk varian `restart` |
| `--sample-size` | 15 | Jumlah sampel neighbor per iterasi untuk varian `stochastic` |
| `--max-no-improve` | 50 | Batas iterasi tanpa peningkatan untuk varian `stochastic` |
| `--show` | tidak aktif | Tampilkan plot interaktif |

Output HC disimpan di subfolder seperti `output/hc_steepest/`, `output/hc_sideways/`, `output/hc_restart/`, dan `output/hc_stochastic/`. File utamanya adalah gambar state awal/akhir, `objective_vs_iter.png`, serta `summary.json`. Jika `--variant all` digunakan, grafik perbandingan antarvarian juga dibuat.

### Simulated Annealing

```bash
python -m src.SA.run_sa input/sample_input.json \
    --runs 3 \
    --max-iter 20000 \
    --objective base \
    --out output
```

| Opsi | Default | Keterangan |
|---|---|---|
| `--runs` | 3 | Jumlah run |
| `--t0` | Rata-rata value paket | Temperatur awal |
| `--alpha` | 0.999 | Faktor pendinginan geometrik, `T ← alpha × T` |
| `--t-min` | 0.1 | Temperatur minimum; pencarian berhenti jika temperatur tidak lagi di atas nilai ini |
| `--max-iter` | 20000 | Batas iterasi maksimum |
| `--objective` | `base` | Objective `base`, `eta`, atau `light` |
| `--seed` | 42 | Seed awal agar eksperimen dapat direproduksi |
| `--out` | `./output` | Direktori dasar output |
| `--show` | tidak aktif | Tampilkan plot interaktif |

Output SA disimpan di `<direktori-output>/sa_<objective>/`, misalnya `output/sa_base/`. Isinya dapat mencakup visualisasi state awal/akhir, `objective_vs_iter.png`, `summary.json`, dan `sa_probability.png` jika ada kandidat dengan objective lebih rendah yang probabilitas penerimaannya dapat diplot.

Metrik SA perlu dibedakan:

- `non_improving_iteration_count` / `non_improving_iteration_frequency`: iterasi ketika tidak ditemukan peningkatan objective terhadap state saat ini. Ini indikator stagnasi, **bukan bukti pasti** bahwa state adalah local optimum.
- `rejected_worse_count`: jumlah kandidat dengan objective lebih rendah yang ditolak.
- `worse_neighbor_rejection_rate`: kandidat lebih buruk yang ditolak dibagi semua kandidat lebih buruk (ditolak + diterima). Jika tidak ada kandidat lebih buruk, nilainya `null` / `N/A`.
- `accepted_worse`: jumlah kandidat lebih buruk yang diterima oleh kriteria Metropolis.
- `no_neighbor`: iterasi ketika tidak berhasil menghasilkan neighbor valid.

### Genetic Algorithm

Contoh menjalankan GA dari root repository:

```bash
python -m src.GA.run_ga input/sample_input.json \
    --runs 3 \
    --population-size 200 \
    --mutation-rate 0.01 \
    --max-generations 200 \
    --objective base \
    --seed 42 \
    --out output
```

| Opsi | Default | Keterangan |
|---|---|---|
| `--runs` | 3 | Jumlah run untuk konfigurasi parameter tersebut |
| `--population-size` | 200 | Ukuran populasi |
| `--mutation-rate` | 0.01 | Probabilitas mutasi individu |
| `--max-generations` | 200 | Jumlah generasi maksimum |
| `--objective` | `violation` | Pilihan `base` atau `violation`; gunakan `base` untuk objective total value dasar |
| `--seed` | 42 | Seed awal; tiap run memakai seed turunan agar run dapat dibedakan dan direproduksi |
| `--out` | `./output` | Direktori dasar output |
| `--show` | tidak aktif | Tampilkan plot interaktif |

Runner menambahkan nama objective ke direktori output. Contoh perintah di atas menghasilkan berkas di `output/ga_base/`, termasuk `summary.json`, `run<N>_initial_final.png`, dan `run<N>_objective_vs_iter.png`.

#### Eksperimen GA sesuai spesifikasi

Spesifikasi meminta dua rangkaian eksperimen, masing-masing berisi 3 konfigurasi × 3 run:

1. **Populasi tetap, jumlah generasi bervariasi.**
2. **Jumlah generasi tetap, ukuran populasi bervariasi.**

Contoh berikut menjalankan kedua rangkaian dari Linux/macOS. Setiap eksekusi membuat direktori batch unik, dan setiap konfigurasi memiliki direktori sendiri sehingga hasil antarkonfigurasi tidak saling menimpa.

```bash
RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
BASE_OUT="output/ga_experiments/${RUN_ID}"

run_ga() {
    local label="$1"
    local population="$2"
    local generations="$3"

    python -m src.GA.run_ga input/sample_input.json \
        --runs 3 \
        --population-size "$population" \
        --mutation-rate 0.01 \
        --max-generations "$generations" \
        --objective base \
        --seed 42 \
        --out "${BASE_OUT}/${label}"
}

# A. Populasi tetap 100; generasi 50, 100, dan 150.
run_ga A_pop100_gen50 100 50
run_ga A_pop100_gen100 100 100
run_ga A_pop100_gen150 100 150

# B. Generasi tetap 100; populasi 25, 50, dan 75.
run_ga B_pop25_gen100 25 100
run_ga B_pop50_gen100 50 100
run_ga B_pop75_gen100 75 100

echo "Hasil eksperimen tersimpan di: ${BASE_OUT}"
```

Karena runner menambahkan folder `ga_base`, masing-masing hasil berada di direktori seperti `${BASE_OUT}/A_pop100_gen50/ga_base/`. Setiap `summary.json` harus berisi 3 run. Simpan nilai populasi dan generasi yang digunakan secara konsisten saat membandingkan hasil.

### Menampilkan bantuan CLI

Untuk melihat opsi yang benar-benar tersedia di runner yang terpasang, jalankan:

```bash
python -m src.HC.run_hc --help
python -m src.SA.run_sa --help
python -m src.GA.run_ga --help
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
- **Stochastic**: Melakukan sampling tetangga on-the-fly yang seimbang antar jenis aksi (swap, move, rotate, insert), lalu memilih secara acak salah satu tetangga yang *strictly better*. Pada implementasi saat ini, `iterations` menghitung percobaan pencarian neighbor, termasuk iterasi ketika tidak ditemukan neighbor yang lebih baik.

## Catatan Implementasi Simulated Annealing

- **Maksimasi**: ΔE = objective(neighbor) − objective(current). Move dengan ΔE ≥ 0 selalu diterima, move yang lebih buruk diterima dengan probabilitas e^(ΔE/T).
- **Neighbor**: satu neighbor valid dipilih acak dari move *swap*, *move*, *rotate*, dan *insert* (maksimal 30 percobaan; jika tidak ada yang valid, iterasi dilewati dan suhu tetap turun).
- **Metrik stagnasi dan penerimaan**: `non_improving_iteration_count` menghitung iterasi ketika neighbor valid tidak meningkatkan objective (atau neighbor valid tidak berhasil dibuat), sedangkan `non_improving_iteration_frequency` membaginya dengan total iterasi. Metrik ini adalah indikator stagnasi, bukan bukti pasti local optimum karena SA hanya memeriksa satu neighbor acak per iterasi. `rejected_worse_count` menghitung kandidat lebih buruk yang ditolak; `worse_neighbor_rejection_rate` membaginya dengan seluruh kandidat lebih buruk, baik yang ditolak maupun diterima. Jika tidak ada kandidat lebih buruk, rejection rate tidak terdefinisi (`null`/`N/A`).
- **Objective bonus**: `eta` (value dibobot urgensi 1 + 1/(1+ETA)) dan `light` (value dikurangi penalti berat kecil). Keduanya tidak menambah variabel baru.

## Pembagian Tugas

| Anggota | NIM | Tugas |
|---|---|---|
| Nathan Adhika S | 13524041 | Fondasi (objective function, validasi, neighbor, input parser) dan Hill-Climbing (semua varian) |
| Muhammad Haris P S | 13524053 | Simulated Annealing, visualisasi, dan Bonus 1 (objective function alternatif) |
| M Iqbal Raihan | 13524011 | Genetic Algorithm dan Bonus 3 |