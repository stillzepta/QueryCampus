"""
Unit tests for QueryCampus Vercel Serverless Entrypoints (api/index.py, server.py, main.py).
"""

import io
import json
import pytest
from api.index import app, handler
import server
import main
import index


def make_request(path: str, method: str = "GET", payload: dict = None, query_string: str = ""):
    """Helper to simulate WSGI request to app callable."""
    body_bytes = json.dumps(payload).encode("utf-8") if payload else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "CONTENT_LENGTH": str(len(body_bytes)),
        "wsgi.input": io.BytesIO(body_bytes),
    }
    response_status = [""]
    response_headers = []

    def start_response(status, headers):
        response_status[0] = status
        response_headers.extend(headers)

    body_chunks = app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return response_status[0], dict(response_headers), body


def test_entrypoint_exports():
    assert hasattr(server, "app")
    assert hasattr(main, "app")
    assert hasattr(index, "app")
    assert hasattr(server, "handler")


def test_vercel_index_html():
    status, headers, body = make_request("/")
    assert "200 OK" in status
    assert "text/html" in headers.get("Content-Type", "")
    assert "QueryCampus" in body


def test_vercel_api_health():
    status, headers, body = make_request("/api/health")
    assert "200 OK" in status
    data = json.loads(body)
    assert data["status"] == "healthy"
    assert "QueryCampus" in data["service"]


def test_vercel_api_stats():
    status, headers, body = make_request("/api/stats")
    assert "200 OK" in status
    data = json.loads(body)
    assert "status" in data
    assert "tickets_count" in data


def test_vercel_api_query_reception_kiosk():
    payload = {"query": "What is the attendance rule?", "model": "gemma3:4b", "top_k": 2}
    status, headers, body = make_request("/api/query", method="POST", payload=payload)
    assert "200 OK" in status
    data = json.loads(body)
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)


def test_vercel_api_chat():
    payload = {
        "query": "What is the minimum attendance requirement?",
        "user_session": {
            "name": "Alex Sharma",
            "email": "student@pesu.pes.edu",
            "role": "Student",
        },
    }
    status, headers, body = make_request("/api/chat", method="POST", payload=payload)
    assert "200 OK" in status
    data = json.loads(body)
    assert "answer" in data
    assert "latency_ms" in data
    assert "confidence_score" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert "requires_ticket" in data


def test_vercel_api_ticket_lifecycle():
    # 1. Create ticket
    payload = {
        "ticket_data": {
            "category": "Lost & Found",
            "summary": "Lost Backpack",
            "query_text": "Left backpack in library 2nd floor",
        },
        "user_session": {
            "name": "Alex Sharma",
            "email": "student@pesu.pes.edu",
            "role": "Student",
        },
    }
    status, headers, body = make_request("/api/ticket", method="POST", payload=payload)
    assert "200 OK" in status
    res = json.loads(body)
    assert res["success"] is True
    assert "ticket_number" in res

    # 2. Get tickets
    status, headers, body = make_request("/api/tickets", method="GET", query_string="role=admin")
    assert "200 OK" in status
    data = json.loads(body)
    assert "tickets" in data
    assert len(data["tickets"]) >= 1


def test_vercel_cors_preflight():
    status, headers, body = make_request("/api/chat", method="OPTIONS")
    assert "200 OK" in status
    assert headers.get("Access-Control-Allow-Origin") == "*"


def test_vercel_auth_login_krishna_admin():
    payload = {"identifier": "krishna@bst.edu.in", "password": "krishna123"}
    status, headers, body = make_request("/api/auth/login", method="POST", payload=payload)
    assert "200 OK" in status
    data = json.loads(body)
    assert data["authenticated"] is True
    assert data["user"]["role"] == "Admin"
    assert data["user"]["email"] == "krishna@bst.edu.in"


def test_vercel_auth_login_amanat_student():
    payload = {"identifier": "amanat@bst.edu.in", "password": "amanat123"}
    status, headers, body = make_request("/api/auth/login", method="POST", payload=payload)
    assert "200 OK" in status
    data = json.loads(body)
    assert data["authenticated"] is True
    assert data["user"]["role"] == "Student"
    assert data["user"]["email"] == "amanat@bst.edu.in"


def test_vercel_auth_login_bare_username():
    payload = {"identifier": "krishna", "password": "krishna123"}
    status, headers, body = make_request("/api/auth/login", method="POST", payload=payload)
    assert "200 OK" in status
    data = json.loads(body)
    assert data["authenticated"] is True
    assert data["user"]["email"] == "krishna@bst.edu.in"


def test_vercel_auth_login_invalid_password():
    payload = {"identifier": "krishna@bst.edu.in", "password": "wrongpassword"}
    status, headers, body = make_request("/api/auth/login", method="POST", payload=payload)
    assert "401" in status
    data = json.loads(body)
    assert data["authenticated"] is False


def test_vercel_auth_login_restricted_non_bst_domain():
    payload = {"identifier": "user@gmail.com", "password": "anypassword"}
    status, headers, body = make_request("/api/auth/login", method="POST", payload=payload)
    assert "403" in status
    data = json.loads(body)
    assert data["authenticated"] is False
    assert "@bst.edu.in" in data["error"]


def test_vercel_auth_fallback_mode_simulation():
    import api.index as idx
    prev = idx.HAS_AUTH_MODULE
    try:
        idx.HAS_AUTH_MODULE = False
        payload = {"identifier": "amanat@bst.edu.in", "password": "amanat123"}
        status, headers, body = make_request("/api/auth/login", method="POST", payload=payload)
        assert "200 OK" in status
        data = json.loads(body)
        assert data["authenticated"] is True
        assert data["user"]["role"] == "Student"
        assert data["user"]["usn"] == "BST24CS001"
    finally:
        idx.HAS_AUTH_MODULE = prev


def test_vercel_api_admin_documents():
    status, headers, body = make_request("/api/admin/documents", method="GET")
    assert "200 OK" in status
    data = json.loads(body)
    assert "documents" in data
    assert isinstance(data["documents"], list)
    assert len(data["documents"]) >= 1
    filenames = [d["filename"] for d in data["documents"]]
    assert any("bosscoder_official_2026_rulebook" in fn for fn in filenames)


def test_vercel_api_admin_upload_authorized():
    import base64
    content = b"Official 2026 Sports Notice: Annual athletics meet scheduled for December 15th."
    b64_str = base64.b64encode(content).decode("utf-8")

    payload = {
        "filename": "sports_notice_2026.txt",
        "file_base64": f"data:text/plain;base64,{b64_str}",
        "user_session": {
            "name": "Krishna Verma",
            "email": "krishna@bst.edu.in",
            "role": "Admin",
        },
    }
    try:
        status, headers, body = make_request("/api/admin/upload", method="POST", payload=payload)
        assert "200 OK" in status
        data = json.loads(body)
        assert data["success"] is True
        assert data["chunks_added"] >= 1
    finally:
        from pathlib import Path
        import os
        target_dir = Path(os.getenv("SAMPLE_DOCS_DIR", "./data/sample_docs"))
        test_file = target_dir / "sports_notice_2026.txt"
        if test_file.exists():
            test_file.unlink()


def test_vercel_api_admin_upload_unauthorized_student():
    import base64
    content = b"Student attempt to upload."
    b64_str = base64.b64encode(content).decode("utf-8")

    payload = {
        "filename": "student_notice.txt",
        "file_base64": b64_str,
        "user_session": {
            "name": "Amanat Singh",
            "email": "amanat@bst.edu.in",
            "role": "Student",
        },
    }
    status, headers, body = make_request("/api/admin/upload", method="POST", payload=payload)
    assert "403" in status
    data = json.loads(body)
    assert data["success"] is False
    assert "Administrator" in data["error"] or "Unauthorized" in data["error"]


def test_vercel_api_ticket_update():
    # 1. Fetch tickets to get an ID
    status, headers, body = make_request("/api/tickets", method="GET", query_string="role=admin")
    assert "200 OK" in status
    data = json.loads(body)
    assert len(data["tickets"]) >= 1
    ticket_id = data["tickets"][0]["id"]

    # 2. Update status and notes
    payload = {
        "ticket_id": ticket_id,
        "new_status": "Resolved",
        "admin_notes": "Official desk verified: Issue resolved by academic supervisor.",
        "user_session": {
            "name": "Krishna Verma",
            "email": "krishna@bst.edu.in",
            "role": "Admin",
        },
    }
    status, headers, body = make_request("/api/ticket/update", method="POST", payload=payload)
    assert "200 OK" in status
    res = json.loads(body)
    assert res["success"] is True


def test_vercel_pure_fallback_mode_simulation():
    """Verify all routes operate cleanly when backend interface is completely unavailable."""
    import api.index as idx
    prev = idx.HAS_BACKEND_INTERFACE
    idx.HAS_BACKEND_INTERFACE = False
    try:
        # GET /
        s, _, b = make_request("/")
        assert "200 OK" in s
        assert "QueryCampus" in b

        # GET /api/tickets
        s, _, b = make_request("/api/tickets", method="GET", query_string="role=student&user_email=amanat@bst.edu.in")
        assert "200 OK" in s
        d = json.loads(b)
        assert "tickets" in d

        # POST /api/ticket
        s, _, b = make_request("/api/ticket", method="POST", payload={"category": "General", "title": "Help", "description": "Details"})
        assert "200 OK" in s
        d = json.loads(b)
        assert d["success"] is True

        # GET /api/admin/documents
        s, _, b = make_request("/api/admin/documents", method="GET")
        assert "200 OK" in s
        d = json.loads(b)
        assert "documents" in d

        # POST /api/query
        s, _, b = make_request("/api/query", method="POST", payload={"query": "exam rules"})
        assert "200 OK" in s
        d = json.loads(b)
        assert "answer" in d
    finally:
        idx.HAS_BACKEND_INTERFACE = prev


def test_vercel_error_boundary_graceful_recovery():
    """Verify that any unexpected crash inside _wsgi_dispatch never escapes as an unhandled 500 Lambda crash."""
    import api.index as idx
    orig_dispatch = idx._wsgi_dispatch
    def crashing_dispatch(environ, start_response):
        raise RuntimeError("Simulated unexpected route dispatch crash")

    idx._wsgi_dispatch = crashing_dispatch
    try:
        # GET / should return 200 with HTML
        s, h, b = make_request("/")
        assert "200 OK" in s
        assert "text/html" in h.get("Content-Type", "")

        # API should return 500 JSON with error info instead of unhandled function invocation failure
        s, h, b = make_request("/api/query", method="POST", payload={"query": "hello"})
        assert "500" in s
        assert "application/json" in h.get("Content-Type", "")
        d = json.loads(b)
        assert d["status"] == "error"
        assert "Simulated unexpected" in d["error"]
    finally:
        idx._wsgi_dispatch = orig_dispatch
