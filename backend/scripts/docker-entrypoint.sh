#!/bin/sh
set -e

# ==============================================================================
# VeriTrace AI — Backend Container Entrypoint
# ==============================================================================

echo "[entrypoint] Starting VeriTrace AI Backend initialization..."

# Apply database migrations
echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
alembic upgrade head || {
    echo "[entrypoint] Database migration initial attempt failed. Retrying in 3 seconds..."
    sleep 3
    alembic upgrade head
}
echo "[entrypoint] Database migrations applied successfully."

# Hand off to CMD
echo "[entrypoint] Handing off to process: $@"
exec "$@"
