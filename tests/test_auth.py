"""Tests for app/auth.py (ABHA Demo Mode auth)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_login_issues_token():
    resp = client.post("/api/auth/demo-login", json={"name": "Dr. Test", "role": "Reviewer"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "ABHA_DEMO"
    assert body["token_type"] == "bearer"
    assert "access_token" in body


def test_whoami_requires_token():
    resp = client.get("/api/auth/whoami")
    assert resp.status_code == 401


def test_whoami_with_valid_token():
    login = client.post("/api/auth/demo-login", json={"name": "Dr. Test", "role": "Reviewer"}).json()
    resp = client.get("/api/auth/whoami", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Dr. Test"


def test_whoami_rejects_garbage_token():
    resp = client.get("/api/auth/whoami", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
