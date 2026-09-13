from datetime import datetime, timedelta
from typing import List, Dict, Optional


def _parse_datetime(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_attlog(body: str) -> List[Dict]:
    """Parse body dari push table=ATTLOG.

    Format standar ZKTeco Push SDK (tab-separated per baris):
        PIN\tDateTime\tStatus\tVerifyType\tWorkCode\t...

    Kalau ternyata format riil di X609/P40 sedikit berbeda (misal ada
    kolom tambahan atau delimiter beda), aktifkan LOG_RAW_REQUESTS=true
    lalu cek `docker compose logs -f app` untuk lihat body asli dan
    sesuaikan parser ini.
    """
    records = []
    for line in body.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        pin = parts[0] if len(parts) > 0 else None
        dt_raw = parts[1] if len(parts) > 1 else None
        status = parts[2] if len(parts) > 2 else None
        verify = parts[3] if len(parts) > 3 else None
        workcode = parts[4] if len(parts) > 4 else None

        records.append(
            {
                "pin": pin,
                "timestamp": _parse_datetime(dt_raw),
                "status": status,
                "verify_type": verify,
                "workcode": workcode,
                "raw_line": line,
            }
        )
    return records


def apply_time_correction(records: List[Dict], correction_seconds: int) -> List[Dict]:
    """Kurangi timestamp tiap record sebanyak `correction_seconds` detik.

    Ini workaround untuk bug firmware yang membuat jam RTC mesin bergeser
    maju (biasanya ~1 jam / 3599 detik) setelah mesin push ke ADMS server.
    Kalau correction_seconds == 0, records dikembalikan apa adanya.
    """
    if not correction_seconds:
        return records

    delta = timedelta(seconds=correction_seconds)
    for r in records:
        if r.get("timestamp") is not None:
            r["timestamp"] = r["timestamp"] - delta
    return records
