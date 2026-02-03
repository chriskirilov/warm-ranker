#!/bin/bash
# Try python3 first, fallback to python
if command -v python3 &> /dev/null; then
    exec python3 api_server.py
elif command -v python &> /dev/null; then
    exec python api_server.py
else
    echo "Error: Python not found" >&2
    exit 1
fi
