"""
MZ BUILDING — point d'entrée backend FastAPI.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    auth, sites, site_status, dashboard, map_layers, contacts, documents,
    docb_aps, contracts, tasks, share, excel_import, reports, audit,
    assistant, rag, geography, ooredoo_centre,
)

logger = logging.getLogger("mz_building")
settings = get_settings()

app = FastAPI(
    title="MZ BUILDING API",
    description="Acquisition & Project Management — MZ Building × Ooredoo Algérie",
    version="1.0.0",
)

# CORS : origines lues depuis .env (CORS_ALLOWED_ORIGINS), jamais "*" avec
# allow_credentials=True (section 82 — audit Phase 21 : c'était figé en dur
# sur localhost:5173 uniquement, non configurable pour un vrai déploiement).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """En-têtes de sécurité HTTP de base (section 82). HTTPS lui-même est
    géré par le reverse proxy en production (Caddy/Nginx) — voir
    docs/SECURITY.md — pas par l'application elle-même."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.on_event("startup")
async def warn_on_default_secrets() -> None:
    """Ne bloque pas le démarrage (une V1 de dev doit pouvoir tourner sans
    friction) mais alerte bruyamment si le secret JWT par défaut est encore
    utilisé — l'oubli le plus dangereux et le plus facile à faire avant un
    vrai déploiement (section 82)."""
    if settings.jwt_secret == "change_moi_en_production":
        logger.warning(
            "\u26a0\ufe0f  JWT_SECRET utilise encore la valeur par défaut de "
            "l'exemple — à changer impérativement avant tout déploiement "
            "accessible publiquement (voir .env)."
        )


app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(site_status.router)
app.include_router(dashboard.router)
app.include_router(map_layers.router)
app.include_router(contacts.router)
app.include_router(documents.router)
app.include_router(docb_aps.router)
app.include_router(contracts.router)
app.include_router(tasks.router)
app.include_router(share.router)
app.include_router(excel_import.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(assistant.router)
app.include_router(rag.router)
app.include_router(geography.router)
app.include_router(ooredoo_centre.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": "mz-building-backend", "version": "1.0.0"}


