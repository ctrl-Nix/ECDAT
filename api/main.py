from fastapi import FastAPI

from api.routers import remediation

app = FastAPI(title="ECDAT API", version="1.0.0")


@app.get("/")
async def health():
    return {"status": "ok", "version": "1.0.0"}


app.include_router(remediation.router, prefix="/scans", tags=["remediation"])
