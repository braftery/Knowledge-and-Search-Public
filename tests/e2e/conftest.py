"""Start one local Streamlit server for the Playwright tests."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VIEWPORT = {"width": 1280, "height": 800}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_healthy(url: str, proc: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 90
    health = url + "/_stcore/health"
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(log_path.read_text()[-4000:])
        try:
            with urllib.request.urlopen(health, timeout=0.5) as response:
                if response.read().strip() == b"ok":
                    return
        except Exception:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("Streamlit did not become healthy.\n" + log_path.read_text()[-4000:])


@pytest.fixture(scope="session")
def app_url():
    """The demo, started with no API key so saved answers stay on."""
    port = _free_port()
    log_path = Path("/tmp/harbor-e2e-streamlit.log")
    log_file = log_path.open("w")
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.address",
            "127.0.0.1",
            "--server.fileWatcherType",
            "none",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_healthy(url, proc, log_path)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()


@pytest.fixture
def page(app_url):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = os.environ.get("HARBOR_CHROMIUM") or None
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        context = browser.new_context(viewport=VIEWPORT)
        tab = context.new_page()
        tab.set_default_timeout(45_000)
        yield tab
        context.close()
        browser.close()


def pytest_collection_modifyitems(config, items):
    """Browser tests start a server and a browser, so they run only when asked: HARBOR_E2E=1 pytest tests/e2e."""
    if os.environ.get("HARBOR_E2E") == "1":
        return
    skip = pytest.mark.skip(reason="Set HARBOR_E2E=1 to run the browser tests.")
    for item in items:
        if "tests/e2e" in str(item.fspath):
            item.add_marker(skip)
