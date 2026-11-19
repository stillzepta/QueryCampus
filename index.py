"""
QueryCampus: Root Index Entrypoint for Vercel.
Module: index.py
Exposes WSGI/ASGI 'app' and HTTP 'handler' for Vercel serverless deployment.
"""

from api.index import app, handler

if __name__ == "__main__":
    import os
    from wsgiref.simple_server import make_server
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 QueryCampus running on http://localhost:{port}")
    with make_server("0.0.0.0", port, app) as httpd:
        httpd.serve_forever()
