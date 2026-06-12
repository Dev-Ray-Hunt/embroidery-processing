"""Tests for the validation web UI backend (POC 2 Step 3).

Structure
---------
* unit (fixture catalogue) — endpoint contracts, validation errors, filters.
  Uses a 10-thread inline catalogue injected via FastAPI dependency override,
  so these run without the gitignored outputs/poc2/madeira_catalogue.json.
* integration — spot-checks against the full built catalogue; skipped if the
  file is absent.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore", message=".*(SciPy|Matplotlib).*")

from fastapi.testclient import TestClient  # noqa: E402

from pocs.poc2_thread_catalogue.src.api import app, get_threads  # noqa: E402
from pocs.poc2_thread_catalogue.src.matching import _rgb_to_lab  # noqa: E402

CATALOGUE_PATH = (
    Path(__file__).resolve().parents[3] / "outputs" / "poc2" / "madeira_catalogue.json"
)
catalogue_present = pytest.mark.skipif(
    not CATALOGUE_PATH.exists(),
    reason="madeira_catalogue.json not present (run catalogue builder first)",
)


def _thread(
    catalog: str,
    name: str,
    rgb: tuple[int, int, int],
    line: str = "Classic Rayon 40",
    family: str = "neutral",
) -> dict:
    return {
        "catalog_number": catalog,
        "color_name": name,
        "brand": f"Madeira {line}",
        "line": line,
        "rgb": list(rgb),
        "hex": "#{:02x}{:02x}{:02x}".format(*rgb),
        "lab": [round(float(v), 4) for v in _rgb_to_lab(rgb)],
        "color_family": family,
        "weight": "40",
        "fiber": "Rayon" if line == "Classic Rayon 40" else "Polyester",
        "conflict": False,
    }


FIXTURE_CATALOGUE = [
    _thread("1000", "Black", (40, 40, 40), family="black"),
    _thread("1001", "Super White", (235, 235, 235), family="white"),
    _thread("1100", "Christmas Red", (182, 15, 47), family="red"),
    _thread("1101", "Royal Blue", (27, 63, 148), family="blue"),
    _thread("1102", "Forest Green", (0, 121, 52), family="green"),
    _thread("1103", "Sunflower", (255, 199, 44), family="yellow"),
    _thread("1104", "Pumpkin", (243, 82, 34), line="Polyneon 40", family="orange"),
    _thread("1105", "Purple", (93, 35, 139), line="Polyneon 40", family="purple"),
    # Duplicate catalog number across lines — mirrors the real 1145 case
    _thread("1145", "Peach Classic", (245, 180, 150)),
    _thread("1145", "Peach Poly", (240, 175, 145), line="Polyneon 40", family="orange"),
]


@pytest.fixture()
def client():
    app.dependency_overrides[get_threads] = lambda: FIXTURE_CATALOGUE
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health + frontend
# ---------------------------------------------------------------------------


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_serves_frontend(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert '<input type="color"' in body
    assert 'id="hex"' in body
    assert "/api/match" in body


# ---------------------------------------------------------------------------
# /api/match
# ---------------------------------------------------------------------------


def test_match_basic_red(client):
    r = client.get("/api/match", params={"color": "b60f2f", "top_n": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["algorithm"] == "ciede2000"
    assert data["input"] == {"hex": "#b60f2f", "rgb": [182, 15, 47]}
    matches = data["matches"]
    assert len(matches) == 3
    top = matches[0]
    assert top["catalog_number"] == "1100"
    assert top["color_name"] == "Christmas Red"
    assert top["hex"] == "#b60f2f"
    assert top["delta_e"] == 0.0
    assert top["rank"] == 1
    # Sorted ascending by delta-E
    des = [m["delta_e"] for m in matches]
    assert des == sorted(des)


def test_match_accepts_hash_prefix(client):
    r = client.get("/api/match", params={"color": "#b60f2f"})
    assert r.status_code == 200
    assert r.json()["matches"][0]["catalog_number"] == "1100"


def test_match_all_algorithms(client):
    r = client.get("/api/match", params={"color": "b60f2f", "algorithm": "all"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert set(results) == {"ciede2000", "cie76", "rgb", "cmc"}
    for matches in results.values():
        assert matches[0]["catalog_number"] == "1100"  # exact hit wins everywhere


def test_match_line_filter(client):
    r = client.get("/api/match", params={"color": "f35222", "line": "Polyneon 40"})
    assert r.status_code == 200
    assert all(m["line"] == "Polyneon 40" for m in r.json()["matches"])


def test_match_validation_errors(client):
    assert client.get("/api/match", params={"color": "zzzzzz"}).status_code == 400
    assert client.get("/api/match", params={"color": "fff"}).status_code == 400
    assert (
        client.get("/api/match", params={"color": "b60f2f", "algorithm": "hsv"}).status_code
        == 400
    )
    assert (
        client.get("/api/match", params={"color": "b60f2f", "line": "Burmilana"}).status_code
        == 400
    )
    assert (
        client.get("/api/match", params={"color": "b60f2f", "top_n": 0}).status_code == 422
    )
    assert (
        client.get("/api/match", params={"color": "b60f2f", "top_n": 51}).status_code == 422
    )


# ---------------------------------------------------------------------------
# /api/catalogue + /api/meta
# ---------------------------------------------------------------------------


def test_catalogue_browse_all(client):
    r = client.get("/api/catalogue")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == len(FIXTURE_CATALOGUE)
    assert {"catalog_number", "color_name", "hex", "rgb", "line", "color_family", "conflict"} <= (
        set(data["threads"][0])
    )


def test_catalogue_family_filter(client):
    r = client.get("/api/catalogue", params={"family": "red"})
    data = r.json()
    assert data["count"] == 1
    assert data["threads"][0]["catalog_number"] == "1100"


def test_catalogue_search_by_name_and_number(client):
    by_name = client.get("/api/catalogue", params={"q": "christmas"}).json()
    assert [t["catalog_number"] for t in by_name["threads"]] == ["1100"]
    by_number = client.get("/api/catalogue", params={"q": "110"}).json()
    assert by_number["count"] == 6  # 1100-1105

    combined = client.get("/api/catalogue", params={"q": "11", "line": "Polyneon 40"}).json()
    assert all(t["line"] == "Polyneon 40" for t in combined["threads"])


def test_catalogue_single_lookup(client):
    r = client.get("/api/catalogue/1101")
    assert r.status_code == 200
    assert r.json()["threads"][0]["color_name"] == "Royal Blue"

    # Duplicate catalog number returns both; line param disambiguates
    both = client.get("/api/catalogue/1145").json()
    assert both["count"] == 2
    one = client.get("/api/catalogue/1145", params={"line": "Polyneon 40"}).json()
    assert one["count"] == 1
    assert one["threads"][0]["color_name"] == "Peach Poly"

    assert client.get("/api/catalogue/9999").status_code == 404


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == len(FIXTURE_CATALOGUE)
    assert data["lines"] == {"Classic Rayon 40": 7, "Polyneon 40": 3}
    assert data["families"]["red"] == 1
    assert set(data["algorithms"]) == {"ciede2000", "cie76", "rgb", "cmc"}


# ---------------------------------------------------------------------------
# Integration: full catalogue (skipped when not built)
# ---------------------------------------------------------------------------


@pytest.fixture()
def real_client():
    return TestClient(app)


@catalogue_present
def test_real_match_known_red(real_client):
    """#C8102E (a classic logo red) must return 1637 Cinnamon Candy as top-1
    under CIEDE2000 — the spot-check verified manually during Step 2."""
    r = real_client.get("/api/match", params={"color": "c8102e", "algorithm": "ciede2000"})
    assert r.status_code == 200
    top = r.json()["matches"][0]
    assert top["catalog_number"] == "1637"
    assert top["delta_e"] < 3.5


@catalogue_present
def test_real_meta_counts(real_client):
    data = real_client.get("/api/meta").json()
    assert data["total"] >= 700  # 823 full build; 706 GPL-only fallback
    assert set(data["lines"]) == {"Classic Rayon 40", "Polyneon 40"}


@catalogue_present
def test_real_catalogue_family_browse(real_client):
    data = real_client.get("/api/catalogue", params={"family": "red"}).json()
    assert data["count"] > 10
    assert all(t["color_family"] == "red" for t in data["threads"])
