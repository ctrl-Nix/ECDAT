from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
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

MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB limit

@app.middleware("http")
async def security_and_limits_middleware(request: Request, call_next):
    # 1. Enforce Payload Size Limit (Step 5)
    if request.method in ("POST", "PUT", "PATCH"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_PAYLOAD_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Payload too large. Maximum allowed size is 5MB."})
    
    response = await call_next(request)
    
    # 2. Inject Security Headers (Step 4)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
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
