"""Validation web UI backend for the Madeira thread catalogue (POC 2 Step 3).

Run from the repo root:

    uv run uvicorn pocs.poc2_thread_catalogue.src.api:app --reload

then open http://127.0.0.1:8000/ for the color-picker UI.

Endpoints
---------
* ``GET /health``                      — liveness + catalogue status
* ``GET /api/meta``                    — lines, color families, algorithms
* ``GET /api/match``                   — color → top-N threads per algorithm
* ``GET /api/catalogue``               — browse/search the catalogue
* ``GET /api/catalogue/{catalog_number}`` — single-number lookup
* ``GET /``                            — the single-file HTML frontend

The catalogue is injected via the ``get_threads`` dependency so tests can
override it with an inline fixture (the real file is gitignored).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from pocs.poc2_thread_catalogue.src.matching import (
    _load_catalogue,
    _parse_color,
    find_closest_threads,
)

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

ALGORITHMS: dict[str, str] = {
    "ciede2000": "A: CIEDE2000",
    "cie76": "B: CIE76",
    "rgb": "C: RGB Euclidean",
    "cmc": "D: CMC l:c 2:1",
}
LINES = ("Classic Rayon 40", "Polyneon 40")

app = FastAPI(title="POC 2 — Madeira Thread Match", version="0.3.0")


def get_threads() -> list[dict]:
    try:
        return _load_catalogue()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Catalogue not built — run "
                "`uv run python -m pocs.poc2_thread_catalogue.src.catalogue` first."
            ),
        ) from None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_hex_or_400(color: str) -> tuple[int, int, int]:
    try:
        return _parse_color(color)
    except ValueError:
        raise HTTPException(400, f"Invalid color {color!r} — expected 6-digit hex.") from None


def _check_line_or_400(line: str | None) -> str | None:
    if line in (None, ""):
        return None
    if line not in LINES:
        raise HTTPException(400, f"Unknown line {line!r} — expected one of {list(LINES)}.")
    return line


def _public_thread(t: dict) -> dict:
    return {
        "catalog_number": t["catalog_number"],
        "color_name": t.get("color_name"),
        "hex": t["hex"],
        "rgb": list(t["rgb"]),
        "line": t["line"],
        "color_family": t.get("color_family"),
        "conflict": t.get("conflict", False),
    }


def _run_match(
    color: str,
    algorithm: str,
    top_n: int,
    line: str | None,
    threads: list[dict],
) -> list[dict]:
    results = find_closest_threads(
        color, top_n=top_n, algorithm=algorithm, line=line, catalogue=threads  # type: ignore[arg-type]
    )
    # MatchResult is a bare tuple; map back to full thread dicts to enrich the
    # response. (catalog_number, rgb) is unique enough — the one duplicate
    # catalog number (1145) differs across lines and RGB values.
    pool = threads if line is None else [t for t in threads if t["line"] == line]
    lookup = {(t["catalog_number"], tuple(t["rgb"])): t for t in pool}
    out = []
    for rank, (number, _name, delta_e, rgb) in enumerate(results, start=1):
        thread = lookup[(number, rgb)]
        out.append({**_public_thread(thread), "rank": rank, "delta_e": round(float(delta_e), 2)})
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    try:
        n = len(_load_catalogue())
    except FileNotFoundError:
        n = None
    return {"status": "ok", "threads": n}


@app.get("/api/meta")
def meta(threads: Annotated[list[dict], Depends(get_threads)]) -> dict:
    lines: dict[str, int] = {}
    families: dict[str, int] = {}
    for t in threads:
        lines[t["line"]] = lines.get(t["line"], 0) + 1
        fam = t.get("color_family") or "unknown"
        families[fam] = families.get(fam, 0) + 1
    return {
        "total": len(threads),
        "lines": lines,
        "families": dict(sorted(families.items())),
        "algorithms": ALGORITHMS,
    }


@app.get("/api/match")
def match(
    color: str,
    threads: Annotated[list[dict], Depends(get_threads)],
    algorithm: str = "ciede2000",
    top_n: int = Query(5, ge=1, le=50),
    line: str | None = None,
) -> dict:
    rgb = _parse_hex_or_400(color)
    line = _check_line_or_400(line)
    if algorithm != "all" and algorithm not in ALGORITHMS:
        raise HTTPException(
            400, f"Unknown algorithm {algorithm!r} — expected {list(ALGORITHMS)} or 'all'."
        )
    base = {
        "input": {"hex": "#{:02x}{:02x}{:02x}".format(*rgb), "rgb": list(rgb)},
        "top_n": top_n,
        "line": line,
    }
    if algorithm == "all":
        return {
            **base,
            "algorithm": "all",
            "results": {a: _run_match(color, a, top_n, line, threads) for a in ALGORITHMS},
        }
    return {
        **base,
        "algorithm": algorithm,
        "matches": _run_match(color, algorithm, top_n, line, threads),
    }


@app.get("/api/catalogue")
def catalogue(
    threads: Annotated[list[dict], Depends(get_threads)],
    family: str | None = None,
    line: str | None = None,
    q: str | None = None,
) -> dict:
    line = _check_line_or_400(line)
    pool = threads
    if line:
        pool = [t for t in pool if t["line"] == line]
    if family:
        pool = [t for t in pool if t.get("color_family") == family]
    if q:
        needle = q.strip().lower()
        pool = [
            t
            for t in pool
            if needle in t["catalog_number"].lower()
            or needle in (t.get("color_name") or "").lower()
        ]
    pool = sorted(pool, key=lambda t: (t["line"], t["catalog_number"]))
    return {"count": len(pool), "threads": [_public_thread(t) for t in pool]}


@app.get("/api/catalogue/{catalog_number}")
def catalogue_one(
    catalog_number: str,
    threads: Annotated[list[dict], Depends(get_threads)],
    line: str | None = None,
) -> dict:
    line = _check_line_or_400(line)
    found = [t for t in threads if t["catalog_number"] == catalog_number]
    if line:
        found = [t for t in found if t["line"] == line]
    if not found:
        raise HTTPException(404, f"No thread with catalog number {catalog_number!r}.")
    return {"count": len(found), "threads": [_public_thread(t) for t in found]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
