# =============================================================================
# Dockerfile — Traffic Analytics Backend
# =============================================================================
# Multi-stage build:
#   builder  — installs dependencies into a virtual environment
#   runtime  — lean image with only the venv
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: builder
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install build tools and libpq (required by psycopg2 / asyncpg compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifest
COPY pyproject.toml .

# Create virtual environment and install all runtime deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the package in editable mode so app/ is importable
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e .

# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Runtime libraries only (libpq for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup pyproject.toml ./pyproject.toml

USER appuser

# Expose application port
EXPOSE 8000

# Health check — Docker will use this to determine container health
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Default command — overridable in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
