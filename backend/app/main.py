from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import audits, patients, quality, snapshots
from .routers.prototype import router as prototype_router

app = FastAPI(title=settings.app_name, version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(snapshots.router, prefix=settings.api_prefix)
app.include_router(quality.router, prefix=settings.api_prefix)
app.include_router(patients.router, prefix=settings.api_prefix)
app.include_router(audits.router, prefix=settings.api_prefix)
app.include_router(prototype_router, prefix=settings.api_prefix)


@app.get("/health")
def healthcheck():
    return {"status": "ok", "service": settings.app_name, "version": "0.3.0"}