#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
npm ci --no-audit --no-fund
.venv/bin/python -m scripts.create_samples
npm run build
echo 'Shortlist: http://127.0.0.1:8000 | recruiter@demo.com / demo123'
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
