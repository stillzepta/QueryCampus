"""
QueryCampus: Root Server Entrypoint for Vercel, Starlette, and Local Execution.
Module: server.py
Exposes WSGI/ASGI 'app' and HTTP 'handler' for Vercel serverless deployment.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import WSGI/ASGI app and HTTP handler from api.index
from api.index import app, handler

# Also alias frontend.server.app if available
try:
    from frontend.server import app as kiosk_app
except Exception:
    kiosk_app = app

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 QueryCampus running on http://localhost:{port}")
    with make_server("0.0.0.0", port, app) as httpd:
        httpd.serve_forever()
