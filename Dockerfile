# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Minimal runtime deps; most Python libs ship wheels for x86_64
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       tzdata \
       libxml2 \
       zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better caching
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project files
COPY src ./src
COPY configs ./configs
COPY scripts ./scripts
COPY pyproject.toml README.md ./

# Default runtime environment can be overridden at run-time
# ENV TZ=America/New_York

# Healthcheck (optional): the app should exit non-zero on failure if added later
# HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import sys; sys.exit(0)"

# Run the bot
ENTRYPOINT ["python","-m","src.bot.app"]
