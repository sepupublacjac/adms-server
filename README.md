# ADMS Server (Custom, Docker-based) — versi database eksternal

Server custom yang mengimplementasikan protokol **ADMS / Push SDK** dari
mesin attendance seperti **Solution X609** dan **ZKTeco P40**.

Versi ini didesain untuk konek ke **Postgres yang sudah kamu install &
jalankan sendiri**, dan langsung `INSERT` ke tabel yang sudah kamu siapkan
(`adms_logs`). Server **tidak membuat tabel apapun** — murni consumer.

## Struktur Project

```
adms-server/
├── app/
│   ├── main.py          # entrypoint FastAPI
│   ├── config.py        # semua setting dibaca dari .env
│   ├── db.py             # koneksi psycopg2 + INSERT/SELECT dinamis
│   ├── parsers.py        # parser format ATTLOG dari mesin
│   └── routers/
│       ├── iclock.py     # endpoint protokol ADMS (/iclock/...)
│       └── admin.py      # lihat data langsung dari tabelmu
├── Dockerfile
├── docker-compose.yml    # hanya service app, tidak ada service db
└── requirements.txt
```

## Setup

```bash
cp .env.example .env
```

Edit `.env`, minimal isi bagian koneksi database:

```env
DB_HOST=host.docker.internal   # atau IP server db kamu
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=xxxx
DB_NAME=nama_database_kamu

ATTENDANCE_TABLE=adms_logs
COL_PIN=user_id
COL_TIMESTAMP=date
COL_STATUS=check_logs
COL_DEVICE_SN=device_sn
```

**Soal `DB_HOST` — penting:**
- Kalau Postgres jalan **di host yang sama** dengan container (misal instalasi native di server yang sama): pakai `host.docker.internal` — sudah otomatis di-setup lewat `extra_hosts` di `docker-compose.yml` (baik di Linux maupun Docker Desktop).
- Kalau Postgres di **server terpisah**: isi langsung IP/hostname server itu, dan pastikan Postgres-nya menerima koneksi dari IP server ADMS (cek `pg_hba.conf` dan `listen_addresses` di `postgresql.conf`, serta firewall port 5432).

Jalankan:

```bash
docker compose up -d --build
```

Cek:
```bash
curl http://localhost:8080/
```

## Konfigurasi di Mesin Attendance

- **Server Address**: IP/domain server tempat container ini jalan
- **Server Port**: `8080` (sesuai `APP_PORT` di `.env`)

## Bagaimana Data Sampai ke `adms_logs`

Saat mesin push data absensi (`POST /iclock/cdata?...&table=ATTLOG`), server:
1. Parse body (format tab-separated: `PIN\tDateTime\tStatus\tVerify\tWorkCode`)
2. Insert langsung ke `ATTENDANCE_TABLE`, memetakan tiap field ke kolom sesuai `.env`:

| Field internal | Env var | Kolom kamu (default) |
|---|---|---|
| PIN / employee ID | `COL_PIN` | `user_id` |
| Timestamp absen | `COL_TIMESTAMP` | `date` |
| Status | `COL_STATUS` | `check_logs` |
| Serial number mesin | `COL_DEVICE_SN` | `device_sn` |
| Verify type (opsional) | `COL_VERIFY_TYPE` | *(kosong = skip)* |
| Work code (opsional) | `COL_WORKCODE` | *(kosong = skip)* |
| Baris mentah (opsional) | `COL_RAW_LINE` | *(kosong = skip)* |

Kalau tabelmu punya kolom tambahan untuk verify_type/workcode/raw baris
mentah, tinggal isi env var-nya dan otomatis ikut di-insert.

## API untuk Cek Data

- `GET /api/logs?device_sn=...&limit=100` — SELECT langsung dari `adms_logs`
- `GET /api/devices` — daftar `device_sn` unik + waktu terakhir muncul (dari isi tabel yang sama)

```bash
curl "http://localhost:8080/api/logs?limit=20"
curl "http://localhost:8080/api/devices"
```

## Endpoint Protokol (referensi)

| Method | Path | Fungsi |
|---|---|---|
| GET | `/iclock/cdata` | Handshake awal, mesin minta konfigurasi |
| POST | `/iclock/cdata` | Mesin push data (`table=ATTLOG` → insert ke tabelmu) |
| GET | `/iclock/getrequest` | Mesin polling command tertunda — **selalu balas OK** (belum ada command queue) |
| POST | `/iclock/devicecmd` | Mesin lapor hasil command — hanya dicatat di log |
| GET/POST | `/iclock/fdata` | Data biometrik/foto — hanya dicatat di log |

> Catatan: fitur kirim command balik ke mesin (misal sync waktu, hapus user)
> butuh tabel command queue. Karena kamu memilih "jangan auto-create
> apapun", fitur itu sengaja tidak diaktifkan di versi ini. Kalau nanti
> mau dipakai, kasih tahu saya nama+struktur tabel command queue yang kamu
> siapkan, saya sambungkan.

## Workaround: Bug Firmware Jam Mesin Bergeser

Kalau mesin kamu kena bug firmware yang bikin RTC bergeser maju (misal
+3599 detik / ~1 jam) setiap kali push ke ADMS, server ini bisa otomatis
mengoreksi timestamp **sebelum** disimpan ke `adms_logs` — tanpa perlu
mengubah jam fisik di mesin.

Set di `.env`:
```env
ATTLOG_TIME_CORRECTION_SECONDS=3599
```

Nilai ini akan **dikurangkan** dari setiap timestamp `ATTLOG` yang masuk.
Beberapa catatan penting:

- Ini cuma berlaku untuk data `table=ATTLOG` (data absensi asli) yang
  masuk ke `adms_logs`. Data `OPERLOG` tetap tidak disimpan seperti
  sebelumnya, jadi tidak perlu dikoreksi.
- Nilai koreksi ini **global** untuk semua device. Kalau nanti kamu punya
  device dengan firmware/perilaku drift yang beda, kabari saya supaya bisa
  saya buat per-device (misal berdasarkan `device_sn`).
- Sebaiknya cek ulang secara berkala (misal tiap beberapa minggu) apakah
  selisihnya tetap konsisten 3599 detik, dengan cara: tap absen sungguhan,
  bandingkan jam asli saat tap vs jam yang tersimpan di `adms_logs`
  ditambah 3599 detik. Kalau drift-nya ternyata bertambah seiring waktu
  (bukan cuma sekali lompat), nilai statis ini perlu disesuaikan lagi atau
  didekati dengan cara lain.
- Ini workaround, bukan perbaikan akar masalah — akar masalahnya ada di
  firmware mesin. Kalau vendor merilis firmware yang memperbaiki ini,
  set `ATTLOG_TIME_CORRECTION_SECONDS=0` lagi.

## Debug Format Data Asli dari Mesin

Set `LOG_RAW_REQUESTS=true` (default sudah aktif), lalu setelah mesin
connect:

```bash
docker compose logs -f app
```

Semua request mentah (query string + body) akan muncul di situ. Kalau
format `ATTLOG` dari X609/P40 ternyata beda urutan/jumlah kolom dari
asumsi standar (`PIN\tDateTime\tStatus\tVerify\tWorkCode`), sesuaikan
`parse_attlog()` di `app/parsers.py`.

## Testing Tanpa Mesin Fisik

Handshake:
```bash
curl "http://localhost:8080/iclock/cdata?SN=TESTSN001&options=all&pushver=2.4.1"
```

Push data absensi (akan langsung ter-insert ke `adms_logs`):
```bash
curl -X POST "http://localhost:8080/iclock/cdata?SN=TESTSN001&table=ATTLOG" \
  --data-binary $'1001\t2026-08-25 08:15:00\t0\t1\t0'
```

Cek hasilnya:
```bash
curl "http://localhost:8080/api/logs"
```

## Catatan Keamanan

- Protokol ADMS asli tidak punya autentikasi (mesin cuma kirim SN). Kalau
  server diekspos ke internet publik: batasi lewat firewall/VPN, atau
  taruh di belakang reverse proxy HTTPS.
- Pastikan user Postgres yang dipakai (`DB_USER`) hanya punya izin yang
  perlu (minimal `INSERT`/`SELECT` ke `adms_logs`), bukan superuser, untuk
  membatasi dampak kalau server ini kena eksploitasi.
