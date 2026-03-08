#!/bin/bash
set -e

# Start the FastAPI application with uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
