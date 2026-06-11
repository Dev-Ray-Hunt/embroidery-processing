"""Build madeira_catalogue.json from the parsed sources.

Merge & reconciliation rule (POC 2 Step 1, documented per NEXT.md):

1. LINE MEMBERSHIP is decided by Madeira USA's official ColorNames lists
   (377 Classic + 409 Polyneon codes). Codes seen only in third-party
   sources are still included but marked `"in_official_names": false`.
2. RGB WINNER is the highest-priority source that has the code:
       official_classic / official_polyneon   (Madeira's own published
                                                swatch colors — authoritative)
     > inkstitch_*                             (open-source, widely used)
     > ezstitch_polyneon                       (explicit RGB text chart)
     > ciainc_polyneon                         (CMYK converted without ICC —
                                                cross-reference only)
   Every source's value is retained in `source_rgb` for auditability.
3. CONFLICTS: if any two sources disagree by more than CONFLICT_DELTA_E
   (CIE76 in Lab — perceptual, not raw RGB), the entry is flagged
   `"conflict": true` for manual/spool validation. It still ships with the
   winning value; flagging is a review queue, not an exclusion.
4. NAMES: official ColorNames list wins; source-provided names fill gaps.

Output schema: see SCHEMA.md. Color family: hue/lightness/saturation
bucketing in HSL — coarse on purpose (editor browse-by-family).
"""

from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np

from pocs.poc2_thread_catalogue.src import sources

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_PATH = REPO_ROOT / "outputs" / "poc2" / "madeira_catalogue.json"

SOURCE_PRIORITY = [
    "official_classic",
    "official_polyneon",
    "inkstitch_rayon",
    "inkstitch_polyneon",
    "ezstitch_polyneon",
    "ciainc_polyneon",
]

CONFLICT_DELTA_E = 18.0  # CIE76; ~2-3x a "clearly noticeable" difference


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB (0-255) -> CIELAB under D65, via colour-science."""
    import colour

    srgb = np.array(rgb, dtype=float) / 255.0
    xyz = colour.sRGB_to_XYZ(srgb)
    lab = colour.XYZ_to_Lab(xyz)  # colour's default illuminant is D65
    return tuple(round(float(v), 2) for v in lab)


def delta_e76(lab1, lab2) -> float:
    return float(np.linalg.norm(np.array(lab1) - np.array(lab2)))


def color_family(rgb: tuple[int, int, int], lab: tuple[float, float, float]) -> str:
    """Coarse family for browse-by-family. Taxonomy from NEXT.md.

    Neutral/white/black gates use Lab (lightness L* + chroma), which handles
    tinted whites like Super White correctly — HSL saturation explodes on
    near-white colors with a faint cast. Hue buckets use HSV hue.
    """
    lightness, a, b_ = lab
    chroma = (a * a + b_ * b_) ** 0.5
    if chroma < 14 and lightness >= 88:
        return "white"
    if lightness <= 20 and chroma < 14:
        return "black"
    if chroma < 12:
        return "neutral"
    r, g, b = (c / 255 for c in rgb)
    deg = colorsys.rgb_to_hsv(r, g, b)[0] * 360
    if 12 <= deg < 42 and (lightness < 45 or chroma < 32):
        return "brown"
    if deg < 12 or deg >= 340:
        return "pink" if lightness >= 70 else "red"
    if deg < 42:  # golds (~44 deg) read as yellow in thread terms
        return "orange"
    if deg < 70:
        return "yellow"
    if deg < 165:
        return "green"
    if deg < 255:
        return "blue"
    if deg < 300:
        return "purple"
    return "pink"


def build() -> dict:
    """Parse every source, merge, reconcile, convert, classify."""
    parsed = {name: fn() for name, fn in sources.ALL_PARSERS.items()}
    names = sources.parse_official_names()

    # catalog -> {source: entry}
    by_code: dict[tuple[str, str], dict[str, dict]] = {}
    for source, entries in parsed.items():
        for e in entries:
            key = (e["line"], e["catalog"])
            by_code.setdefault(key, {})[source] = e

    threads = []
    conflicts = 0
    for (line, catalog), per_source in sorted(by_code.items()):
        winner_source = next(s for s in SOURCE_PRIORITY if s in per_source)
        rgb = tuple(per_source[winner_source]["rgb"])
        lab = rgb_to_lab(rgb)

        # Conflict check across sources, in Lab. ciainc is excluded from the
        # FLAG (its CMYK->RGB conversion has no ICC profile, so moderate
        # drift is expected and documented) but kept in source_rgb for audit.
        labs = {
            s: rgb_to_lab(tuple(e["rgb"])) for s, e in per_source.items() if s != "ciainc_polyneon"
        }
        max_de = 0.0
        for s1 in labs:
            for s2 in labs:
                max_de = max(max_de, delta_e76(labs[s1], labs[s2]))
        conflict = max_de > CONFLICT_DELTA_E
        conflicts += conflict

        official_name = names.get(line, {}).get(catalog)
        fallback_name = next(
            (
                per_source[s]["name"]
                for s in SOURCE_PRIORITY
                if s in per_source and per_source[s]["name"]
            ),
            None,
        )
        threads.append(
            {
                "catalog_number": catalog,
                "color_name": official_name or fallback_name,
                "brand": f"Madeira {line}",
                "line": line,
                "rgb": list(rgb),
                "hex": "#{:02x}{:02x}{:02x}".format(*rgb),
                "lab": list(lab),
                "color_family": color_family(rgb, lab),
                "weight": "40",
                "fiber": "Rayon" if line == sources.LINE_CLASSIC else "Polyester",
                "rgb_source": winner_source,
                "source_rgb": {s: list(e["rgb"]) for s, e in sorted(per_source.items())},
                "in_official_names": official_name is not None,
                "conflict": conflict,
                "max_source_delta_e": round(max_de, 1),
            }
        )

    lines_count = {}
    for t in threads:
        lines_count[t["line"]] = lines_count.get(t["line"], 0) + 1
    return {
        "schema_version": 1,
        "threads": threads,
        "stats": {
            "total": len(threads),
            "per_line": lines_count,
            "conflicts": conflicts,
            "sources": {k: len(v) for k, v in parsed.items()},
        },
    }


def main() -> int:
    catalogue = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(catalogue, indent=1))
    s = catalogue["stats"]
    print(f"{s['total']} threads -> {OUT_PATH}")
    print(f"per line: {s['per_line']}")
    print(f"flagged conflicts: {s['conflicts']}")
    print(f"per source: {s['sources']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
