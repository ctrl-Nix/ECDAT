import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import settings
from api.routers import cbom, findings, remediation, report_sync, scans

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Enterprise Cryptographic Discovery & Assessment Tool API",
)

# CORS middleware for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=bool(settings.CORS_ORIGINS),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-ECDAT-Agent-ID"],
)

MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB limit
logger = logging.getLogger("ecdat.audit")

@app.middleware("http")
async def security_and_limits_middleware(request: Request, call_next):
    request_id = str(uuid4())
    # State-changing API routes accept canonical JSON only. This prevents a
    # browser form post from being interpreted as a report-bundle submission.
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return JSONResponse(
                status_code=415,
                content={"detail": "Content-Type must be application/json"},
                headers={"X-Request-ID": request_id},
            )

    # Enforce advertised payload-size limit before handlers parse a body.
    if request.method in ("POST", "PUT", "PATCH"):
        content_length = request.headers.get("content-length")
        limit = (
            settings.REPORT_SYNC_MAX_BUNDLE_BYTES
            if request.url.path.startswith("/agent/v1/report-bundles")
            else MAX_PAYLOAD_SIZE
        )
        if content_length and content_length.isdigit() and int(content_length) > limit:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Payload too large. Maximum allowed size is {limit} bytes."},
                headers={"X-Request-ID": request_id},
            )
    
    response = await call_next(request)
    
    # Inject security headers; the TLS gateway remains the authoritative HSTS
    # issuer for public traffic. Direct local HTTP development avoids receiving
    # a sticky HSTS policy accidentally.
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "ecdat_request request_id=%s method=%s path=%s status=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
    )
    
    return response


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

# POST /agent/v1/report-bundles — authenticated scanner-agent intake only.
app.include_router(report_sync.router)
