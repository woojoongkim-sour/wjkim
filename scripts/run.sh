#!/bin/bash
set -e

echo "Installing dependencies..."
poetry install

echo "Running database migrations..."
poetry run alembic upgrade head

echo "Starting development server..."
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
