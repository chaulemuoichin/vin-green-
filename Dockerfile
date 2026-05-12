# Multi-stage Dockerfile for Hanoi Air Forecast
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies into venv
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only. `curl` is needed for the container
# healthchecks declared in docker-compose / docker-compose.prod.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    liblapack3 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ /app/src/
COPY data/ /app/data/
COPY app/ /app/app/
COPY api/ /app/api/
COPY worker/ /app/worker/
COPY scripts/ /app/scripts/
COPY pyproject.toml .env.example ./

# Set PYTHONUNBUFFERED to get logs immediately
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Switch to non-root user
RUN chown -R app:app /app
USER app

# Default command (can be overridden by docker-compose)
CMD ["streamlit", "run", "/app/app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
