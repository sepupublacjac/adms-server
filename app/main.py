import logging

from fastapi import FastAPI

from .routers import admin, iclock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="ADMS Server",
    description=(
        "Custom ADMS / Push SDK server, kompatibel dengan mesin attendance "
        "berbasis protokol ZKTeco (Solution X609, ZKTeco P40, dll). "
        "Menulis langsung ke tabel Postgres yang sudah kamu siapkan."
    ),
)

app.include_router(iclock.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "adms-server"}
