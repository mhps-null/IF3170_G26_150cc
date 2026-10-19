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
│   ├── visualization.py   # plot 3D state dan grafik eksperimen
│   ├── SA/                # Simulated Annealing, objective bonus, runner
│   ├── GA/                # Genetic Algorithm, objective penalti, runner
│   └── hill_climbing.py   # Hill-Climbing (semua varian)
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

Jalankan dari folder `src/`.

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

- `run<N>_initial_final.png`: visualisasi 3D state awal dan akhir (paket di dalam dan di luar truk, value, berat),
- `objective_vs_iter.png`: nilai objective function per iterasi,
- `sa_probability.png`: nilai e^(ΔE/T) per iterasi,
- `summary.json`: parameter, durasi, jumlah iterasi, frekuensi *stuck*, serta state awal dan akhir.

**Genetic Algorithm**

```bash
python GA/run_ga.py ../input/<nama_file>.json --runs 3 --out ../output
```

| Opsi | Default | Keterangan |
|---|---|---|
| `--runs` | 3 | jumlah run |
| `--population-size` | 200 | jumlah individu tiap generasi |
| `--mutation-rate` | 0.01 | peluang satu anak dimutasi |
| `--max-generations` | 200 | jumlah generasi (iterasi) |
| `--objective` | `violation` | `violation` atau `base` |
| `--seed` | 42 | seed acak agar hasil dapat direproduksi |
| `--show` | – | tampilkan jendela plot |

Hasil tiap run disimpan di `output/ga_<objective>/`:

- `run<N>_initial_final.png`: visualisasi 3D individu terbaik di populasi awal dan individu terbaik di akhir,
- `run<N>_objective_vs_iter.png`: nilai objective maksimum dan rata-rata populasi per generasi,
- `summary.json`: parameter, ukuran populasi, jumlah iterasi, durasi, nilai objective akhir, serta state awal dan akhir.

**Hill-Climbing**

```bash
# lengkapi sesuai file masing-masing
python <path_ke_runner> ../input/<nama_file>.json
```

## Catatan Implementasi Simulated Annealing

- **Maksimasi**: ΔE = objective(neighbor) − objective(current). Move dengan ΔE ≥ 0 selalu diterima, move yang lebih buruk diterima dengan probabilitas e^(ΔE/T).
- **Neighbor**: satu neighbor valid dipilih acak dari move *swap*, *move*, *rotate*, dan *insert* (maksimal 30 percobaan; jika tidak ada yang valid, iterasi dilewati dan suhu tetap turun).
- **Stuck**: iterasi di mana neighbor yang lebih buruk ditolak sehingga SA bertahan di state yang sama. Frekuensinya = jumlah stuck / jumlah iterasi.
- **Objective bonus**: `eta` (value dibobot urgensi 1 + 1/(1+ETA)) dan `light` (value dikurangi penalti berat kecil). Keduanya tidak menambah variabel baru.

## Catatan Implementasi Genetic Algorithm

- **Representasi**: satu individu adalah satu state pengepakan. Populasi awal diisi state acak yang valid.
- **Seleksi orang tua**: roulette wheel. Bobot tiap individu digeser dengan nilai absolut fitness terendah di populasi generasi itu, lalu dihitung sekali untuk seluruh pemilihan pada generasi tersebut.
- **Crossover**: single-point pada urutan id paket. Anak dapat melanggar batasan.
- **Mutasi**: dengan peluang `mutation_rate`, anak diganti satu neighbor valid dari move *swap*, *move*, *rotate*, atau *insert*. Jika tidak ada neighbor valid, anak tidak berubah.
- **Pergantian generasi**: μ + λ. Orang tua dan anak digabung, lalu `population_size` individu dengan fitness tertinggi dipertahankan.
- **Objective `violation`**: fitness = value dasar − (total value seluruh paket + 1) × besar pelanggaran. Pelanggaran mencakup kelebihan berat, volume di luar truk, volume tumpang tindih, luas kontak di atas paket *fragile*, dan jejak paket yang melayang. State valid selalu mengalahkan state yang melanggar. `final_base_value` di `summary.json` tetap total value paket yang terangkut.

## Pembagian Tugas

| Anggota | NIM | Tugas |
|---|---|---|
| _Nathan Adhika S_ | _13524041_ | Fondasi (objective function, validasi, neighbor, input parser) dan Hill-Climbing (semua varian) |
| _Muhammad Haris P S_ | _13524053_ | Simulated Annealing, visualisasi, dan Bonus 1 (objective function alternatif) |
| _M Iqbal Raihan_ | _NIM_ | Genetic Algorithm dan Bonus 3 |