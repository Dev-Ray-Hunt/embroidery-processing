"""Shared fixtures for POC 2 browser tests (mirrors the POC 1 pattern)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE_PATH = REPO_ROOT / "outputs" / "poc2" / "madeira_catalogue.json"


@pytest.fixture(scope="session")
def live_server():
    """A real uvicorn serving the validation UI, for browser tests."""
    import subprocess
    import sys
    import time
    import urllib.request

    if not CATALOGUE_PATH.exists():
        pytest.skip("madeira_catalogue.json not present (run catalogue builder first)")

    port = 8912  # poc1's bake-off conftest uses 8911
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "pocs.poc2_thread_catalogue.src.api:app",
            "--port",
            str(port),
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            pytest.fail("validation UI server did not become ready")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def pw():
    """The ONE sync Playwright instance for this test session (the sync API
    allows a single instance per thread)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")
    p = sync_playwright().start()
    yield p
    p.stop()


@pytest.fixture(scope="session")
def browser_page(pw, live_server):
    """A Chromium page on the live server; skips if chromium isn't installed.

    Collects page errors and console errors into ``page.collected_errors`` so
    tests can assert the page ran clean.
    """
    try:
        browser = pw.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"chromium unavailable: {e}")
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on(
        "console",
        lambda msg: errors.append(f"console.error: {msg.text}") if msg.type == "error" else None,
    )
    page.collected_errors = errors
    page.base_url_poc2 = live_server
    yield page
    browser.close()
