# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.5.0
COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
RUN groupadd --gid 1001 appgroup \
 && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/
COPY pyproject.toml .
RUN mkdir -p /app/documents && chown appuser:appgroup /app/documents
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","2"]
