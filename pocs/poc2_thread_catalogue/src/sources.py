"""Parsers for the Madeira color-data sources in data/madeira_sources/.

Every parser returns a list of normalized entries:

    {"catalog": "1610", "name": "..."|None, "rgb": (r, g, b), "line": "...",
     "source": "<source id>"}

Sources (provenance + retrieval dates in data/README.md):

- official_classic   — Madeira's 2023 Colour_Cards.pdf. The CLASSIC 40 card's
                       "Index of Colors" page carries one JPEG thumbnail per
                       thread with its catalog number printed immediately to
                       the right; we decode each thumbnail and take the mean
                       color of its central crop.
- official_polyneon  — Madeira's MADEIRA_POLYNEON.pdf shade card: 18 large
                       vector panels per page, one color each, catalog number
                       printed on the panel.
- ciainc_polyneon    — CIA Inc.'s Polyneon chart: 100 vector swatch bars per
                       page, number adjacent to each bar.
- ezstitch_polyneon  — EZ Stitch Digitizing's Polyneon 40 chart: plain text
                       rows with explicit RGB triplets. (Upstream filename
                       says classic_40, but the title page and 1500-1999 code
                       range identify it as Polyneon.)
- names              — Madeira USA's official ColorNames PDFs (catalog
                       number -> color name, both lines; no RGB).
"""

from __future__ import annotations

import io
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_DIR = REPO_ROOT / "data" / "madeira_sources"

LINE_CLASSIC = "Classic Rayon 40"
LINE_POLYNEON = "Polyneon 40"


def _rgb255(color) -> tuple[int, int, int] | None:
    """PDF non-stroking color -> (r, g, b) 0-255.

    Handles gray (1 component), RGB (3) and CMYK (4 — converted naively,
    without ICC; sources using CMYK are treated as low-precision
    cross-references during reconciliation, never as the winning value).
    """
    if color is None:
        return None
    if isinstance(color, (int, float)):
        color = (color, color, color)
    if len(color) == 1:
        color = (color[0],) * 3
    if len(color) == 4:
        c, m, y, k = (float(v) for v in color)
        color = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    if len(color) != 3:
        return None
    return tuple(round(float(c) * 255) for c in color)


def _catalog_words(page) -> list[dict]:
    """4-digit number words with their centers."""
    out = []
    for w in page.extract_words():
        t = w["text"].strip().rstrip("•")
        if t.isdigit() and len(t) == 4:
            out.append({"text": t, "x": (w["x0"] + w["x1"]) / 2, "y": (w["top"] + w["bottom"]) / 2})
    return out


def _filled_rects(page, w_range, h_range) -> list[dict]:
    out = []
    for r in page.rects:
        if not r.get("fill"):
            continue
        if not (w_range[0] <= r["width"] <= w_range[1] and h_range[0] <= r["height"] <= h_range[1]):
            continue
        rgb = _rgb255(r.get("non_stroking_color"))
        if rgb is None:
            continue
        out.append(
            {
                "x": (r["x0"] + r["x1"]) / 2,
                "y": (r["top"] + r["bottom"]) / 2,
                "x0": r["x0"],
                "x1": r["x1"],
                "top": r["top"],
                "bottom": r["bottom"],
                "rgb": rgb,
            }
        )
    return out


def _pair_nearest(swatches: list[dict], numbers: list[dict], *, max_dist: float) -> list[tuple]:
    """Greedy globally-nearest pairing; pairs beyond max_dist stay unmatched."""
    candidates = []
    for si, s in enumerate(swatches):
        for ni, n in enumerate(numbers):
            d = ((s["x"] - n["x"]) ** 2 + (s["y"] - n["y"]) ** 2) ** 0.5
            if d <= max_dist:
                candidates.append((d, si, ni))
    candidates.sort(key=lambda c: c[0])
    used_s: set[int] = set()
    used_n: set[int] = set()
    pairs = []
    for _, si, ni in candidates:
        if si in used_s or ni in used_n:
            continue
        used_s.add(si)
        used_n.add(ni)
        pairs.append((swatches[si], numbers[ni]))
    return pairs


def parse_official_classic() -> list[dict]:
    """CLASSIC index page: one JPEG thumbnail per thread, catalog number
    printed beside it (left of it in some columns, right in others)."""
    import pdfplumber
    from PIL import Image, ImageStat

    path = SOURCES_DIR / "madeira_official_colour_cards.pdf"
    out: dict[str, tuple[int, int, int]] = {}
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[2]  # pages 2-11 are identical copies of the index
        numbers = _catalog_words(page)
        swatches: list[dict] = []
        for im in page.images:
            try:
                img = Image.open(io.BytesIO(im["stream"].get_data())).convert("RGB")
            except Exception:  # noqa: BLE001 — non-swatch furniture image
                continue
            w, h = img.size
            crop = img.crop(
                (w // 4, h // 4, max(w // 4 + 1, 3 * w // 4), max(h // 4 + 1, 3 * h // 4))
            )
            stat = ImageStat.Stat(crop)
            if max(stat.stddev) > 28:
                continue  # not a flat swatch (logo, photo, gradient art)
            rgb = tuple(round(v) for v in stat.mean)
            swatches.append(
                {
                    "x": (im["x0"] + im["x1"]) / 2,
                    "y": (im["top"] + im["bottom"]) / 2,
                    "x0": im["x0"],
                    "x1": im["x1"],
                    "rgb": rgb,
                }
            )
        # Index layout (verified visually): each cell is `NUMBER [swatch]`,
        # number always LEFT of its swatch. A symmetric rule would let a
        # swatch claim the NEXT column's number across the gutter, so pair
        # strictly leftward: number center within 45pt left of the swatch's
        # left edge, same row, globally nearest first.
        candidates = []
        for si, s in enumerate(swatches):
            for ni, n in enumerate(numbers):
                if abs(n["y"] - s["y"]) > 6:
                    continue
                gap = s["x0"] - n["x"]
                if 0 <= gap <= 45:
                    candidates.append((gap + 5 * abs(n["y"] - s["y"]), si, ni))
        candidates.sort(key=lambda c: c[0])
        used_s: set[int] = set()
        used_n: set[int] = set()
        for _, si, ni in candidates:
            if si in used_s or ni in used_n:
                continue
            used_s.add(si)
            used_n.add(ni)
            code = numbers[ni]["text"]
            # Classic Rayon 40 catalog numbers span 1000-1499.
            if 1000 <= int(code) <= 1499:
                out.setdefault(code, swatches[si]["rgb"])
    return [
        {"catalog": c, "name": None, "rgb": rgb, "line": LINE_CLASSIC, "source": "official_classic"}
        for c, rgb in sorted(out.items())
    ]


def parse_official_polyneon() -> list[dict]:
    """Dedicated Polyneon shade card: 18 large one-color panels per page."""
    import pdfplumber

    path = SOURCES_DIR / "madeira_official_polyneon.pdf"
    out: dict[str, tuple[int, int, int]] = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            panels = _filled_rects(page, (300, 520), (120, 260))
            numbers = _catalog_words(page)
            if not panels or not numbers:
                continue
            # The number is printed on (or right next to) its panel: prefer
            # containment, fall back to nearest within half a panel.
            for n in numbers:
                inside = [
                    p
                    for p in panels
                    if p["x0"] <= n["x"] <= p["x1"] and p["top"] <= n["y"] <= p["bottom"]
                ]
                target = None
                if len(inside) == 1:
                    target = inside[0]
                else:
                    near = sorted(
                        panels,
                        key=lambda p: (p["x"] - n["x"]) ** 2 + (p["y"] - n["y"]) ** 2,
                    )
                    if near:
                        d = ((near[0]["x"] - n["x"]) ** 2 + (near[0]["y"] - n["y"]) ** 2) ** 0.5
                        if d < 250:
                            target = near[0]
                if target is not None:
                    out.setdefault(n["text"], target["rgb"])
    return [
        {
            "catalog": c,
            "name": None,
            "rgb": rgb,
            "line": LINE_POLYNEON,
            "source": "official_polyneon",
        }
        for c, rgb in sorted(out.items())
    ]


def parse_ciainc_polyneon() -> list[dict]:
    """CIA Inc. chart: 100 swatch bars (~72x18) per page, number adjacent."""
    import pdfplumber

    path = SOURCES_DIR / "ciainc_polyneon.pdf"
    out: dict[str, tuple[int, int, int]] = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            bars = _filled_rects(page, (50, 100), (10, 30))
            numbers = _catalog_words(page)
            for s, n in _pair_nearest(bars, numbers, max_dist=60):
                out.setdefault(n["text"], s["rgb"])
    return [
        {"catalog": c, "name": None, "rgb": rgb, "line": LINE_POLYNEON, "source": "ciainc_polyneon"}
        for c, rgb in sorted(out.items())
    ]


def parse_ezstitch_polyneon() -> list[dict]:
    """EZ Stitch chart: plain text rows `CODE NAME R, G, B`."""
    import pdfplumber

    path = SOURCES_DIR / "ezstitch_madeira_classic_40.pdf"
    row = re.compile(r"^(\d{4})\s+(.+?)\s+(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})$")
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                m = row.match(line.strip())
                if not m:
                    continue
                rgb = tuple(int(m.group(i)) for i in (3, 4, 5))
                if not all(0 <= c <= 255 for c in rgb):
                    continue
                out.append(
                    {
                        "catalog": m.group(1),
                        "name": m.group(2).strip(),
                        "rgb": rgb,
                        "line": LINE_POLYNEON,
                        "source": "ezstitch_polyneon",
                    }
                )
    return out


def parse_official_names() -> dict[str, dict[str, str]]:
    """Madeira USA ColorNames PDFs -> {line: {catalog: official name}}."""
    import pdfplumber

    name_re = re.compile(r"(\d{4})•?\s+([A-Za-z][A-Za-z0-9 .'&/()-]*?)(?=\s+\d{4}|$)")
    out: dict[str, dict[str, str]] = {LINE_CLASSIC: {}, LINE_POLYNEON: {}}
    for fname, line in [
        ("madeirausa_classic_names.pdf", LINE_CLASSIC),
        ("madeirausa_polyneon_names.pdf", LINE_POLYNEON),
    ]:
        with pdfplumber.open(SOURCES_DIR / fname) as pdf:
            for page in pdf.pages:
                for text_line in (page.extract_text() or "").splitlines():
                    for code, name in name_re.findall(text_line):
                        name = name.strip()
                        # Reject technical-spec fragments the layout sometimes
                        # places next to a number (e.g. "dtex 200 x 2").
                        if "dtex" in name.lower() or len(name) < 3:
                            continue
                        out[line].setdefault(code, name)
    return out


def _parse_gpl(path: Path) -> list[tuple[str, str, tuple[int, int, int]]]:
    """GIMP palette rows -> [(catalog, name, rgb)]. Format per line:
    `R G B <whitespace> Name <whitespace> NUMBER`."""
    rows = []
    pat = re.compile(r"^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s+(.*?)\s+(\d{3,4})\s*$")
    for line in path.read_text().splitlines():
        if line.startswith(("GIMP", "Name:", "Columns:", "#")):
            continue
        m = pat.match(line)
        if not m:
            continue
        rgb = tuple(int(m.group(i)) for i in (1, 2, 3))
        if all(0 <= c <= 255 for c in rgb):
            rows.append((m.group(5), m.group(4).strip(), rgb))
    return rows


def parse_inkstitch_rayon() -> list[dict]:
    """Ink/Stitch's Madeira Rayon palette (GPL-licensed open source) — the
    only source covering the full Classic 1000-1499 range with names."""
    return [
        {
            "catalog": code,
            "name": name,
            "rgb": rgb,
            "line": LINE_CLASSIC,
            "source": "inkstitch_rayon",
        }
        for code, name, rgb in _parse_gpl(SOURCES_DIR / "inkstitch_madeira_rayon.gpl")
    ]


def parse_inkstitch_polyneon() -> list[dict]:
    """Ink/Stitch's Madeira Polyneon palette."""
    return [
        {
            "catalog": code,
            "name": name,
            "rgb": rgb,
            "line": LINE_POLYNEON,
            "source": "inkstitch_polyneon",
        }
        for code, name, rgb in _parse_gpl(SOURCES_DIR / "inkstitch_madeira_polyneon.gpl")
    ]


def parse_inkstitch_isacord() -> list[dict]:
    """Ink/Stitch's Isacord palette — POC 2 Task 2 cross-reference brand,
    not merged into the Madeira catalogue."""
    return [
        {
            "catalog": code,
            "name": name,
            "rgb": rgb,
            "line": "Isacord 40",
            "source": "inkstitch_isacord",
        }
        for code, name, rgb in _parse_gpl(SOURCES_DIR / "inkstitch_isacord.gpl")
    ]


ALL_PARSERS = {
    "official_classic": parse_official_classic,
    "official_polyneon": parse_official_polyneon,
    "ciainc_polyneon": parse_ciainc_polyneon,
    "ezstitch_polyneon": parse_ezstitch_polyneon,
    "inkstitch_rayon": parse_inkstitch_rayon,
    "inkstitch_polyneon": parse_inkstitch_polyneon,
}
