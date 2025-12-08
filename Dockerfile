# Y6 Practice Exam System - Docker Image
# Multi-stage build for smaller image size

FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim-bookworm

LABEL maintainer="Spring Gate Private School"
LABEL description="Y6 Practice Exam System for Primary School Students"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Make scripts executable and create command wrapper
RUN chmod +x /app/docker/entrypoint.sh /app/docker/setup-wizard.py 2>/dev/null || true \
    && echo '#!/bin/bash\nexec /app/docker/entrypoint.sh "$@"' > /usr/local/bin/y6 \
    && chmod +x /usr/local/bin/y6

# Environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Kuala_Lumpur \
    APP_ENV=production \
    CONFIG_DIR=/app/config \
    DATA_DIR=/app/data

# Create directories for persistent data
RUN mkdir -p /app/config /app/data /app/logs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Entrypoint
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["serve"]
