import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routers import documents, query, stream

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="DocMind")

app.include_router(documents.router)
app.include_router(query.router)
app.include_router(stream.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
