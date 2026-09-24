FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system ecdat && adduser --system --ingroup ecdat --home /nonexistent ecdat

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=ecdat:ecdat . .
RUN pip install --no-cache-dir -e .

USER ecdat
EXPOSE 8000
# Container image tarballs can be mounted read-only at runtime via `docker run -v ...:ro`

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
