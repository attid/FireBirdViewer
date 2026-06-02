# ---------- Stage 1: Build frontend assets ----------
FROM node:20-slim AS frontend

WORKDIR /build

# Install npm dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source files needed for Tailwind content scanning + build
COPY tailwind.config.js ./
COPY static/src/ static/src/
COPY src/ src/
COPY main.py ./

# Build all vendor assets (CSS + CodeMirror bundle + HTMX copy)
RUN mkdir -p static/vendor && npm run build


# ---------- Stage 2: Python runtime ----------
FROM python:3.13-slim

# Optional build-time override. If omitted, app falls back to VERSION file.
ARG VERSION=""
ENV APP_VERSION=${VERSION}

# Firebird Python driver requires the native client library at runtime.
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends libfbclient2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY main.py ./
COPY VERSION ./
COPY src/ src/
COPY static/app.js static/app.js
COPY static/codemirror-init.js static/codemirror-init.js
COPY static/favicon.ico static/favicon.ico

# Copy built vendor assets from frontend stage
COPY --from=frontend /build/static/vendor/ static/vendor/

EXPOSE 5001

CMD ["uv", "run", "python", "main.py"]
