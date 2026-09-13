from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Koneksi ke database Postgres yang SUDAH ADA (tidak dibuat oleh server ini)
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = ""
    db_name: str = "postgres"

    # Nama tabel yang sudah kamu siapkan untuk menampung data absensi
    attendance_table: str = "adms_logs"

    # Mapping field internal -> nama kolom di tabelmu.
    # Kosongkan (biarkan None) kalau kolomnya memang tidak ada di tabelmu,
    # field itu akan otomatis di-skip saat INSERT.
    col_pin: str = "user_id"
    col_timestamp: str = "date"
    col_status: str = "check_logs"
    col_device_sn: Optional[str] = "device_sn"
    col_verify_type: Optional[str] = None
    col_workcode: Optional[str] = None
    col_raw_line: Optional[str] = None

    # Kalau True, isi request mentah dari mesin ditulis ke stdout container
    # (lihat lewat `docker compose logs -f app`) -- berguna untuk cek format
    # asli tanpa perlu bikin tabel baru.
    log_raw_requests: bool = True

    # Workaround untuk bug firmware: jam RTC mesin bergeser (biasanya +1 jam)
    # setelah mesin melakukan push ke ADMS server. Nilai ini (dalam detik)
    # akan DIKURANGKAN dari timestamp ATTLOG sebelum disimpan ke DB.
    # Contoh: kalau mesin konsisten 3599 detik lebih cepat, isi 3599 (positif),
    # nanti otomatis dikurangkan. Isi 0 untuk mematikan koreksi ini.
    attlog_time_correction_seconds: int = 0

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
