#!/bin/bash
set -e
python3 mediainfo_check.py
gunicorn app:app --bind 0.0.0.0:${PORT:-8000} &
exec python3 bot.py
