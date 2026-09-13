import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from .. import db
from ..config import settings
from ..parsers import apply_time_correction, parse_attlog

router = APIRouter(prefix="/iclock", tags=["iclock"])
logger = logging.getLogger("adms.iclock")


def _log_raw(method: str, path: str, request: Request, body: str = ""):
    if settings.log_raw_requests:
        logger.info(
            "RAW %s %s | query=%s | body=%s",
            method,
            path,
            str(request.query_params),
            body[:1000],
        )


@router.get("/cdata")
def handshake(
    request: Request,
    SN: str = Query(...),
    options: str = Query(None),
    pushver: str = Query(None),
):
    """Handshake awal saat mesin baru konek / minta konfigurasi (options=all)."""
    _log_raw("GET", "/iclock/cdata", request)

    lines = [
        f"GET OPTION FROM: {SN}",
        "Stamp=0",
        "OpStamp=0",
        "ErrorDelay=60",
        "Delay=30",
        "TransTimes=00:00;14:05",
        "TransInterval=1",
        "TransFlag=1111000000",
        "Realtime=1",
        "Encrypt=None",
    ]
    return PlainTextResponse("\n".join(lines))


@router.post("/cdata")
async def push_data(
    request: Request,
    SN: str = Query(...),
    table: str = Query(None),
    Stamp: str = Query(None),
):
    """Mesin push data absensi ke sini. table=ATTLOG akan langsung di-INSERT
    ke tabel yang sudah kamu siapkan (lihat .env)."""
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8", errors="replace")
    _log_raw("POST", "/iclock/cdata", request, body)

    if table == "ATTLOG":
        records = parse_attlog(body)
        if settings.attlog_time_correction_seconds:
            records = apply_time_correction(records, settings.attlog_time_correction_seconds)
        inserted = db.insert_attendance_records(records, device_sn=SN)
        logger.info(
            "Insert %d baris attendance dari SN=%s (koreksi=%ss)",
            inserted,
            SN,
            settings.attlog_time_correction_seconds,
        )
    else:
        # table lain (OPERLOG, BIODATA, USERINFO, dll) untuk sementara hanya
        # dicatat di log (lihat log_raw_requests) -- belum di-insert ke DB
        # karena belum ada tabel tujuan untuk itu.
        logger.info("Terima table=%s dari SN=%s (belum di-handle, cek raw log)", table, SN)

    return PlainTextResponse("OK")


@router.get("/getrequest")
def get_request(request: Request, SN: str = Query(...)):
    """Mesin polling command tertunda. Server ini belum punya command queue
    (tidak ada tabel untuk itu), jadi selalu balas OK / tidak ada command."""
    _log_raw("GET", "/iclock/getrequest", request)
    return PlainTextResponse("OK")


@router.post("/devicecmd")
async def device_cmd_result(request: Request, SN: str = Query(...)):
    """Mesin lapor hasil eksekusi command. Karena belum ada command queue,
    hasil ini hanya dicatat di log."""
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8", errors="replace")
    _log_raw("POST", "/iclock/devicecmd", request, body)
    return PlainTextResponse("OK")


@router.get("/fdata")
@router.post("/fdata")
async def biophoto(request: Request):
    """Data biometrik/foto (opsional, tergantung fitur mesin) -- dicatat di log saja."""
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8", errors="replace")
    _log_raw(request.method, "/iclock/fdata", request, body)
    return PlainTextResponse("OK")
