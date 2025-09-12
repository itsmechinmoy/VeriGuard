#!/bin/bash

# Check if PORT is set, default to 8000 if not
PORT=${PORT:-8000}

# Run uvicorn with the port
exec uvicorn main:app --host 0.0.0.0 --port $PORT