# ============================================================
# AI SQL Analyst — backend image
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# System dependency needed for psycopg2 to compile/link against
# libpq. Installed and left in a single RUN layer to keep the
# image small — no separate apt-get cache lingering in a later layer.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST, before the rest of the source code.
# This is a deliberate layer-caching optimization: Docker rebuilds
# a layer only when its inputs change. If only app code changes
# (the common case during development), this pip install layer is
# reused from cache instead of re-running — a full dependency
# reinstall only happens when requirements.txt itself changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code
COPY app ./app

EXPOSE 8000

# No --reload here: --reload is a development convenience (file
# watching) with real overhead, and has no place in a production-
# style container. Compose will override this command for local
# dev if we want hot reload — see docker-compose.yml's command override.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]