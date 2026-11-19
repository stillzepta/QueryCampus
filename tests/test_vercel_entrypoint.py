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
