from typing import Optional

from fastapi import APIRouter

from .. import db

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/devices")
def list_devices():
    """Daftar device_sn unik yang pernah kirim data, berdasarkan isi tabelmu."""
    return db.fetch_known_devices()


@router.get("/logs")
def list_logs(device_sn: Optional[str] = None, limit: int = 100):
    """Lihat data terbaru langsung dari tabel yang kamu siapkan."""
    return db.fetch_recent_logs(device_sn, limit)
