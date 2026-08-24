from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import settings
from api.routers import cbom, findings, remediation, scans

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Enterprise Cryptographic Discovery & Assessment Tool API",
)

# CORS middleware for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
@app.get("/", tags=["health"])
async def health():
    return {"status": "ok", "version": settings.API_VERSION}


# --- Routers ---
# POST /scans, GET /scans, GET /scans/{id}
app.include_router(scans.router)

# GET /scans/{scan_id}/findings, GET /scans/{scan_id}/findings/{finding_id}
app.include_router(findings.router)

# GET /scans/{scan_id}/cbom
app.include_router(cbom.router)

# GET /scans/{id}/remediation/{finding_id}
app.include_router(remediation.router, prefix="/scans")
