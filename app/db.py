import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.pool

from .config import settings

logger = logging.getLogger("adms.db")

_pool = psycopg2.pool.SimpleConnectionPool(
    1,
    10,
    host=settings.db_host,
    port=settings.db_port,
    user=settings.db_user,
    password=settings.db_password,
    dbname=settings.db_name,
)


@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def _column_mapping():
    """Map field internal -> nama kolom tujuan, hanya field yang kolomnya
    di-set di config yang akan ikut di-INSERT."""
    mapping = {
        settings.col_pin: "pin",
        settings.col_timestamp: "timestamp",
        settings.col_status: "status",
    }
    if settings.col_device_sn:
        mapping[settings.col_device_sn] = "device_sn"
    if settings.col_verify_type:
        mapping[settings.col_verify_type] = "verify_type"
    if settings.col_workcode:
        mapping[settings.col_workcode] = "workcode"
    if settings.col_raw_line:
        mapping[settings.col_raw_line] = "raw_line"
    return mapping


def insert_attendance_records(records: list[dict], device_sn: str) -> int:
    """Insert parsed attendance records ke tabel yang sudah kamu siapkan
    (settings.attendance_table), memakai mapping kolom dari .env.
    Return jumlah baris yang berhasil di-insert.
    """
    if not records:
        return 0

    mapping = _column_mapping()
    columns = list(mapping.keys())
    fields = list(mapping.values())

    col_list = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f'INSERT INTO "{settings.attendance_table}" ({col_list}) VALUES ({placeholders})'

    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for r in records:
                row = {**r, "device_sn": device_sn}
                values = [row.get(f) for f in fields]
                cur.execute(sql, values)
                inserted += 1

    return inserted


def fetch_recent_logs(device_sn: str | None, limit: int):
    mapping = _column_mapping()
    # kolom -> field, dibalik lagi untuk SELECT
    select_cols = list(mapping.keys())
    col_list = ", ".join(f'"{c}"' for c in select_cols)

    sql = f'SELECT {col_list} FROM "{settings.attendance_table}"'
    params = []
    if device_sn and settings.col_device_sn:
        sql += f' WHERE "{settings.col_device_sn}" = %s'
        params.append(device_sn)
    sql += f' ORDER BY "{settings.col_timestamp}" DESC LIMIT %s'
    params.append(limit)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
    return [dict(zip(colnames, row)) for row in rows]


def fetch_known_devices():
    if not settings.col_device_sn:
        return []
    sql = (
        f'SELECT "{settings.col_device_sn}" AS device_sn, '
        f'MAX("{settings.col_timestamp}") AS last_seen '
        f'FROM "{settings.attendance_table}" '
        f'GROUP BY "{settings.col_device_sn}"'
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [{"device_sn": r[0], "last_seen": r[1]} for r in rows]
