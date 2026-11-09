"""Isolated session files and a live-call counter that tests do not share with the machine."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HARBOR_API_SESSIONS", str(tmp_path))
    monkeypatch.setenv("HARBOR_LIVE_CAP_FILE", str(tmp_path / "live-cap.json"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def short(client):
    response = client.post("/api/session/jump-short")
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def started(client):
    response = client.post("/api/session/reset", json={"mode": "start"})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def explore(client):
    response = client.post("/api/explore/open", json={"role": "Pharmacy advocate"})
    assert response.status_code == 200, response.text
    return client


def open_role(client, role: str):
    response = client.post("/api/explore/open", json={"role": role})
    assert response.status_code == 200, response.text
    return client


def session_dir(client) -> str:
    root = os.environ["HARBOR_API_SESSIONS"]
    return os.path.join(root, client.cookies["harbor_session"])
