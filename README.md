# IF3170 Tugas Besar 1 - Local Search

Kelompok **G26 – 150cc**

Repository ini berisi implementasi algoritma *local search* untuk masalah **pengepakan paket ke dalam satu atau beberapa truk** (Mejiro Express). Satu truk maupun banyak truk sama-sama direpresentasikan sebagai *fleet*. Tujuannya adalah memilih paket lalu menentukan truk, posisi, dan orientasinya agar **total value paket yang terangkut pada seluruh fleet maksimum**, dengan batasan berikut diperiksa pada tiap truk:

- paket tidak keluar dari ruang truk yang ditempatinya dan tidak saling tumpang tindih,
- total berat pada truk itu tidak melebihi kapasitasnya,
- paket tidak boleh melayang (harus ditopang lantai atau paket lain di truk yang sama),
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
│   ├── foundation.py      # Fleet, Truck, Package, State, objective, validasi, neighbor
│   ├── visualization.py   # Visualisasi 3D tiap truk dan plot hasil eksperimen
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

File JSON di folder `input/`. Satu truk memakai kunci `truck`. Beberapa truk memakai kunci `trucks`; tiap truk punya `id`.

```json
{
  "truck": {"w": 10, "l": 20, "h": 5, "maxCapacity": 500},
  "packages": [
    {"id": "P01", "w": 4, "l": 3, "h": 4, "value": 32, "weight": 9, "is_fragile": false, "eta": 3}
  ]
}
```

```json
{
  "trucks": [
    {"id": "T1", "w": 10, "l": 16, "h": 5, "maxCapacity": 420},
    {"id": "T2", "w": 10, "l": 14, "h": 5, "maxCapacity": 360}
  ],
  "packages": [
    {"id": "P01", "w": 4, "l": 3, "h": 4, "value": 32, "weight": 9, "is_fragile": false, "eta": 3}
  ]
}
```

`input/sample_input.json` adalah satu truk dengan 30 paket. `input/multitruck.json` adalah dua truk dengan 50 paket; atribut paketnya diulang dari katalog sampel, dengan id `P01`–`P50`. Jika `truck` tidak memuat `id`, id truk menjadi `T1`. Penempatan internal menyimpan `truck_id`. Pada fleet satu truk, `truck_id` boleh kosong dan penempatan dianggap milik truk itu.

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

Modul `src/foundation.py` memuat `Fleet`, `Truck`, `Package`, `PackagePlacement`, dan `State`, plus validasi, parser JSON, dan pembangkitan tetangga. `parse_input` selalu mengembalikan `(Fleet, catalog)`. Objective dasar (`State.get_objective_value`) menjumlahkan value setiap paket yang penempatannya bukan `None`, tanpa memandang truk.

- **Validasi State** (`State.is_valid`): representasi harus memuat tepat semua id paket. Pemeriksaan berikut dilakukan terpisah pada tiap truk, sehingga paket di truk lain tidak bisa saling menopang atau bertumpuk:
  - *Dimensi*: paket berada di dalam ruang truknya ($x+w \le W$, $y+l \le L$, $z+h \le H$).
  - *Kapasitas Berat*: total berat paket di truk itu tidak melampaui `maxCapacity`.
  - *Overlap*: tidak ada dua paket di truk yang sama yang saling tumpang tindih.
  - *Penopang Fisik*: paket tidak boleh melayang; setiap paket bertumpu pada lantai ($z=0$) atau tepat di atas permukaan atas paket lain di truk yang sama.
  - *Proteksi Fragile*: paket `is_fragile = true` tidak boleh menopang paket lain.
  - `truck_id` yang tidak ada di fleet membuat state tidak valid.
- **Operator Tetangga** (`State.generate_neighbors`): hanya neighbor yang lolos `is_valid` yang dikembalikan.
  - **MOVE**: menggeser paket di dalam truknya secara lokal ($\pm$ `max_shift` pada $x$ dan $y$, lalu $z$ pada tingkat penopang truk itu).
  - **SWAP**: menukar seluruh penempatan dua paket, termasuk koordinat, orientasi, dan `truck_id`.
  - **ROTATE**: rotasi $90^\circ$ pada satu sumbu. Dari $(w, l, h)$ hanya ada tiga hasil: $(l, w, h)$, $(w, h, l)$, dan $(h, l, w)$.
  - **INSERT**: memasukkan paket dari luar ke salah satu truk, dengan orientasi acak dan posisi pada tingkat penopang truk itu.
  - **TRANSFER**: jika fleet punya lebih dari satu truk, memindahkan paket yang sudah termuat ke truk lain dengan cara sampling yang sama seperti INSERT.
- Mode tanpa `sample_size` (Steepest Ascent dan Sideways) mengenumerasi swap, move, dan rotasi, lalu mengambil sampai `insert_tries` kandidat insert per paket luar per truk dan sejumlah yang sama untuk transfer. Mode `sample_size` (Stochastic Hill-Climbing dan mutasi GA) memilih jenis aksi yang tersedia secara seragam, termasuk transfer bila ada lebih dari satu truk.

## Catatan Implementasi Hill-Climbing

- **Steepest Ascent**: memakai neighborhood lengkap di atas, dengan INSERT dan TRANSFER di-sample (`insert_tries`, default 50). Tetangga bernilai tertinggi yang dipilih; jika beberapa sama baik, salah satunya diambil acak. Jika tidak ada tetangga, atau tetangga terbaik tidak lebih baik dari state sekarang, seluruh neighborhood dibuat ulang sampai `max_resamples=3`. Pencarian berhenti setelah itu, tanpa menjamin optimum lokal terhadap seluruh posisi yang mungkin.
- **Sideways Move**: neighborhood yang sama. Perpindahan ke tetangga bernilai sama diizinkan sampai `max_sideways` (default 50, dihitung berturut-turut). `--cumulative` mengubah penghitung itu menjadi kumulatif. Pencarian juga berhenti, setelah resampling yang sama, bila tidak ada tetangga yang nilainya sama atau lebih baik.
- **Random Restart**: menjalankan Steepest Ascent sebanyak `max_restart` dari state awal acak yang baru tiap restart, lalu menyimpan solusi bernilai tertinggi. `summary.json` memuat `restart_iterations` dan `restart_indices`. Plot objective memisahkan riwayat tiap restart.
- **Stochastic**: mengambil `sample_size` neighbor acak (default 15) dengan jenis aksi yang tersedia dipilih seragam, termasuk transfer pada fleet lebih dari satu truk, lalu memilih acak di antara neighbor yang nilainya lebih tinggi. `iterations` menghitung setiap percobaan, termasuk percobaan yang tidak menemukan neighbor lebih baik. Pencarian berhenti setelah `max_no_improve` percobaan berturut-turut tanpa peningkatan.

## Catatan Implementasi Simulated Annealing

- **Maksimasi**: ΔE = objective(neighbor) − objective(current). Move dengan ΔE ≥ 0 selalu diterima, move yang lebih buruk diterima dengan probabilitas e^(ΔE/T).
- **Neighbor**: satu neighbor valid dipilih acak dari *swap*, *move*, *rotate*, dan *insert*. Pada fleet lebih dari satu truk, *transfer* ikut menjadi pilihan. Maksimal 30 percobaan; jika tidak ada yang valid, iterasi dilewati dan suhu tetap turun. Move dan rotate tetap di truk pemilik paket. Insert memilih truk secara acak.
- **Metrik stagnasi dan penerimaan**: `non_improving_iteration_count` menghitung iterasi ketika neighbor valid tidak meningkatkan objective (atau neighbor valid tidak berhasil dibuat), sedangkan `non_improving_iteration_frequency` membaginya dengan total iterasi. Metrik ini adalah indikator stagnasi, bukan bukti pasti local optimum karena SA hanya memeriksa satu neighbor acak per iterasi. `rejected_worse_count` menghitung kandidat lebih buruk yang ditolak; `worse_neighbor_rejection_rate` membaginya dengan seluruh kandidat lebih buruk, baik yang ditolak maupun diterima. Jika tidak ada kandidat lebih buruk, rejection rate tidak terdefinisi (`null`/`N/A`).
- **Objective bonus**: `eta` menjumlahkan `value * (1 + 1/(1+ETA))` untuk setiap paket yang termuat. `light` menjumlahkan `value - 0.1 * weight`. Keduanya hanya melihat penempatan yang bukan `None`, sehingga berlaku sama untuk satu truk maupun fleet. Keduanya tidak menambah variabel baru.

## Catatan Implementasi Genetic Algorithm

- **Individu**: satu state valid beserta fitness-nya. State awal acak dibuat dengan mencoba tiap paket pada lantai salah satu truk; paket yang membuat fleet tidak valid dikembalikan ke luar.
- **Seleksi**: roulette. Tiap generasi, bobot dihitung sekali dengan menggeser fitness sebesar nilai absolut fitness terendah. Geseran itu hanya dipakai untuk mengundi, tidak ditulis kembali ke fitness tersimpan. Jika total bobot 0, induk dipilih seragam.
- **Crossover**: satu titik potong pada urutan id katalog. Anak yang tidak valid diperbaiki dengan memasang kembali paket dari $z$ terendah dan membuang paket yang membuat fleet tidak valid.
- **Mutasi**: dengan probabilitas `mutation_rate`, individu diganti oleh satu neighbor acak dari `generate_neighbors(sample_size=15)`. Jika tidak ada neighbor, salinan individu dipertahankan.
- **Penggantian**: $\mu+\lambda$. Induk dan anak digabung, lalu `population_size` individu berfitness tertinggi dipertahankan.
- **Objective**: `base` adalah total value paket termuat. `violation`, default runner, mengurangi value itu dengan `(jumlah seluruh value paket + 1)` kali total pelanggaran pada semua truk. Pada state valid, penalti nol, sehingga nilainya sama dengan `base`. Fitness GA hanya dihitung untuk state valid.
- **Laporan**: `iterations` adalah `max_generations`. Plot `run<N>_objective_vs_iter.png` memuat objective maksimum dan rata-rata populasi, dicatat sekali sebelum generasi pertama dan sekali sesudah tiap generasi. `summary.json` menyimpan ukuran populasi, durasi, objective akhir, value dasar awal dan akhir, serta state awal dan akhir. State awal pada gambar adalah individu terbaik di populasi awal.

## Visualisasi

`src/visualization.py` menggambar satu panel 3D untuk tiap truk. Fleet satu truk memakai judul "State Awal" dan "State Akhir". Fleet beberapa truk menyusun tiap truk sebagai baris, dengan state awal di kolom kiri dan state akhir di kolom kanan. Panel teks memuat value total, jumlah paket di dalam dan di luar, serta berat, kapasitas, jumlah paket, dan ukuran tiap truk. Paket fragile memakai garis tepi merah tebal. Plot angka (`objective_vs_iter`, probabilitas SA, kemajuan GA, dan perbandingan nilai akhir) tidak bergantung pada jumlah truk.

## Pembagian Tugas

| Anggota | NIM | Tugas |
|---|---|---|
| Nathan Adhika S | 13524041 | Laporan, Fondasi (objective function, validasi, neighbor, input parser) dan Hill-Climbing (semua varian) |
| Muhammad Haris P S | 13524053 | Laporan, Simulated Annealing, visualisasi, dan Bonus 1 (objective function alternatif) |
| M Iqbal Raihan | 13524011 | Genetic Algorithm dan Bonus 3 |