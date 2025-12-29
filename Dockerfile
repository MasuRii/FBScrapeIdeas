# ==========================================
# Build Stage
# ==========================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from lockfile
COPY requirements.lock .
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock

# ==========================================
# Production Stage
# ==========================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright \
    SCRAPER_ENGINE=playwright

WORKDIR /app

# Install runtime dependencies including Playwright system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Initialize Playwright and install Chromium
RUN python -m playwright install chromium && \
    python -m playwright install-deps chromium

# Set permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check entrypoint
# Note: In a CLI tool, health check can be run manually via `docker exec`
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
