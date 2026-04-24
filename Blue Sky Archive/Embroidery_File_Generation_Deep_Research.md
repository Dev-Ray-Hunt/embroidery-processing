# Image-to-Embroidery File Generation: Deep Research Brief

## For Barudan Machines via BNet Software

---

## TL;DR

Converting raster images to machine-embroidery files for Barudan machines is a multi-stage pipeline: image segmentation and vectorization, stitch-type assignment, stitch path generation, physical compensation, path optimization, and finally binary encoding into a machine-readable format (DST for universal compatibility or DSB for Barudan-native features). The open-source ecosystem provides strong building blocks — **pyembroidery** (Python) handles all format I/O including DST writing, **Ink/Stitch** demonstrates production-quality auto-fill and satin algorithms, and **stitch-generator** provides clean algorithmic primitives for stitch pattern generation. No single library does end-to-end image-to-stitch conversion, so you will need to build the digitizing intelligence (image analysis, region classification, stitch type assignment, compensation) yourself, using these libraries as the read/write and stitch-generation layers. The DST format is a compact 3-byte-per-stitch binary protocol with a 512-byte header, delta-encoded coordinates, and a ternary bit-packing scheme that is well-documented and straightforward to implement.

---

## Table of Contents

1. [Context and Scope](#context-and-scope)
2. [Target File Formats](#target-file-formats)
3. [DST Format Technical Specification](#dst-format-technical-specification)
4. [DSB Format and Barudan-Specific Considerations](#dsb-format)
5. [BNet Software Integration](#bnet-integration)
6. [Open-Source Libraries](#open-source-libraries)
7. [The Image-to-Embroidery Pipeline](#pipeline)
8. [Core Algorithms: Stitch Generation](#stitch-generation-algorithms)
9. [Physical Compensation Algorithms](#physical-compensation)
10. [Path Optimization](#path-optimization)
11. [Adjacent Opportunities](#adjacent-opportunities)
12. [Competing Perspectives and Counterarguments](#counterarguments)
13. [Decision Points](#decision-points)
14. [Horizon: Worth Knowing About](#horizon)
15. [Sources and Confidence](#sources)

---

## 1. Context and Scope {#context-and-scope}

**Core question:** What technology, libraries, algorithms, and file format specifications are needed to build a software tool that takes a raster image as input and produces embroidery machine files compatible with Barudan machines running BNet software?

**Frameworks used:** Product & Feature Research playbook (build-vs-buy analysis, implementation reality), Root Cause Analysis (understanding the digitizing pipeline), Analogous Industry Scan (borrowing from CNC/CAM toolpath generation).

**In scope:** File format specifications (DST, DSB), open-source libraries, digitizing algorithms (fill, satin, running stitch), image processing pipeline, path optimization, physical compensation, BNet compatibility requirements.

**Out of scope:** Commercial digitizing software evaluations, specific fabric/thread databases, production workflow management, BNet administrative features unrelated to file loading.

---

## 2. Target File Formats {#target-file-formats}

### Format Hierarchy for Barudan + BNet

For Barudan machines running BNet software, there are three relevant formats in order of priority:

**DST (Data Stitch Tajima)** — The universal embroidery interchange format. Every commercial embroidery machine on the market reads DST. It is the safest target format for your project because it guarantees compatibility not just with Barudan but with any machine you might ever need to support. BNet and Barudan's TES software both natively accept DST files. The tradeoff is that DST stores no color information — only stitch coordinates and color-change commands. The operator must manually assign thread colors on the machine or in BNet.

**DSB (Design Stitch Barudan)** — Barudan's proprietary format that extends DST with embedded color data and Barudan-specific machine instructions. DSB files store thread color assignments directly, which eliminates manual color setup on the machine and reduces operator error in multi-color production runs. If your production environment is exclusively Barudan, DSB should be the primary output format. The tradeoff is that DSB is poorly documented publicly and has limited open-source support (pyembroidery can read DSB but does not write it as of the latest release).

**U03 / FDR-3** — Barudan's newer proprietary format offering enhanced color management, stitch precision, and thumbnail preview support. This is the most feature-rich Barudan format, but it is the least publicly documented and has essentially no open-source tooling support.

### Recommended Strategy

Build your pipeline to target **DST as the primary output format**. DST is fully specified, has excellent library support, and works with every machine. If Barudan-specific features (embedded colors, machine instructions) are needed later, you can add DSB output as a secondary format — but this will require reverse-engineering from existing DSB files or working with Barudan's proprietary SDK.

---

## 3. DST Format Technical Specification {#dst-format-technical-specification}

The DST format was created by Tajima and has become the de facto industry standard. It is a compact binary format with two sections: a fixed-size header and a variable-length body of 3-byte stitch records.

### 3.1 File Structure Overview

```
[512-byte Header] [3-byte stitch records...] [END marker]
```

**File validation rule:** `(file_size - 512) % 3 == 0` — this is always true for valid DST files and can be used for format detection.

### 3.2 Header Format (512 bytes)

The header is 125 bytes of ASCII metadata padded with `0x20` (space characters) to 512 bytes total. Fields are fixed-width and identified by two-character prefixes:

| Field | Offset | Length | Description | Example |
|-------|--------|--------|-------------|---------|
| `LA:` | 0 | 20 | Design label/name (16 chars + padding) | `LA:MyDesign         \r` |
| `ST:` | 20 | 11 | Total stitch count (7 digits, zero-padded) | `ST:0012345\r` |
| `CO:` | 31 | 7 | Number of color changes (3 digits) | `CO:007\r` |
| `+X:` | 38 | 9 | Positive X extent in 0.1mm units (5 digits) | `+X:00234\r` |
| `-X:` | 47 | 9 | Negative X extent in 0.1mm units (5 digits) | `-X:00123\r` |
| `+Y:` | 56 | 9 | Positive Y extent in 0.1mm units (5 digits) | `+Y:00456\r` |
| `-Y:` | 65 | 9 | Negative Y extent in 0.1mm units (5 digits) | `-Y:00078\r` |
| `AX:` | 74 | 10 | End-of-design needle X offset (signed) | `AX:+00000\r` |
| `AY:` | 84 | 10 | End-of-design needle Y offset (signed) | `AY:+00000\r` |
| `MX:` | 94 | 10 | Reserved / previous design offset X | `MX:+00000\r` |
| `MY:` | 104 | 10 | Reserved / previous design offset Y | `MY:+00000\r` |
| `PD:` | 114 | 10 | Previous design identifier | `PD:******\r` |
| Pad | 124 | 388 | Padding with `0x20` to reach 512 bytes | |

Fields end with `\r` (carriage return, `0x0D`). Numeric values are ASCII-encoded, zero-padded, right-aligned.

**Extended headers:** Some modern implementations add color information after the standard header area. Pyembroidery supports writing extended DST headers that include thread color sequences, but this is non-standard and may be ignored by some machines.

### 3.3 Stitch Record Encoding (3-Byte Ternary System)

Each stitch in the body is encoded as exactly 3 bytes. The format uses a **ternary encoding** system where each axis displacement (X and Y) is encoded across scattered bits in all three bytes. This encoding scheme is sometimes called "Tajima Ternary."

#### Bit Layout

Each 3-byte record encodes: a delta-X displacement, a delta-Y displacement, and control flags.

```
Byte 1 (bits 7-0):  y7  y6  y5  y4  x7  x6  x5  x4
Byte 2 (bits 7-0):  y3  y2  y1  y0  x3  x2  x1  x0
Byte 3 (bits 7-0):  y8  x8  y9  x9  C1  C0  S1  S0
```

Where:
- `x0`–`x9` and `y0`–`y9` are displacement bits for X and Y axes
- `C0`, `C1` are control bits (color change / stop)
- `S0`, `S1` are stitch-type bits

#### Displacement Decoding

The X and Y displacements use a **ternary** system. Each pair of bits represents one of three values:

| Bit pair | Value | Movement |
|----------|-------|----------|
| `00` | 0 | No movement for this component |
| `01` | +1 | Positive direction |
| `10` | -1 | Negative direction |
| `11` | 0 | No movement (same as 00) |

The bits are weighted by powers, so each bit pair contributes a specific magnitude:

| Bits | Weight (in 0.1mm increments) |
|------|------------------------------|
| `x0/y0` (byte 2, lower bits) | 1 (0.1mm) |
| `x1/y1` (byte 2) | 2 (0.2mm) |
| `x2/y2` (byte 2) | 4 (0.4mm) |
| `x3/y3` (byte 2) | 8 (0.8mm) |
| `x4/y4` (byte 1) | 16 (1.6mm) |
| `x5/y5` (byte 1) | 32 (3.2mm) |
| `x6/y6` (byte 1) | 64 (6.4mm) |
| `x7/y7` (byte 1) | Not standard / extended |
| `x8/y8` (byte 3) | Not standard / extended |
| `x9/y9` (byte 3) | Not standard / extended |

**Maximum single-stitch displacement:** Using standard bits (0-6), the maximum displacement in any axis is `1 + 2 + 4 + 8 + 16 + 32 + 64 = ±121 units = ±12.1mm`. This is the well-known 12.1mm max stitch length of DST files.

**Resolution:** 0.1mm per unit (1 unit = 0.1mm = 10 microns).

#### Control Flags (Byte 3, lower bits)

| Bits [1:0] of byte 3 | Meaning |
|-----------------------|---------|
| `00` | Normal stitch |
| `01` | Jump stitch (move without stitching) |
| `10` | Color change / Stop |
| `11` | End of design (typically `0x00 0x00 0xF3`) |

**Important nuance:** The "color change" and "stop" commands are the same bit pattern. The machine interprets them contextually — a color change followed by stitches is treated as a thread swap, while consecutive stops may pause the machine for operator intervention. Many machines auto-trigger a trim after 3-5 consecutive jump stitches.

#### End-of-Design Marker

The standard end-of-file sequence is three bytes: `0x00 0x00 0xF3`. Some implementations write additional padding after this marker.

### 3.4 Pseudocode: Writing a DST File

```python
def write_dst(pattern, filename):
    with open(filename, 'wb') as f:
        # 1. Write 512-byte header
        header = format_header(pattern)
        f.write(header.ljust(512, b'\x20'))

        # 2. Write stitch records
        prev_x, prev_y = 0, 0
        for stitch in pattern.stitches:
            dx = stitch.x - prev_x
            dy = stitch.y - prev_y

            # Split large movements into multiple records
            while abs(dx) > 121 or abs(dy) > 121:
                clip_dx = max(-121, min(121, dx))
                clip_dy = max(-121, min(121, dy))
                f.write(encode_record(clip_dx, clip_dy, JUMP))
                dx -= clip_dx
                dy -= clip_dy

            f.write(encode_record(dx, dy, stitch.command))
            prev_x, prev_y = stitch.x, stitch.y

        # 3. Write end marker
        f.write(b'\x00\x00\xF3')

def encode_record(dx, dy, command):
    """Encode a single 3-byte DST stitch record."""
    b = [0, 0, 0x03]  # byte3 starts with bits set

    # Encode Y displacement into scattered bits
    if dy > 0:
        if dy & 1:   b[1] |= 0x80  # y0: +1
        if dy & 2:   b[1] |= 0x40  # y1: +2
        if dy & 4:   b[1] |= 0x20  # y2: +4
        if dy & 8:   b[1] |= 0x10  # y3: +8
        if dy & 16:  b[0] |= 0x80  # y4: +16
        if dy & 32:  b[0] |= 0x40  # y5: +32
        if dy & 64:  b[0] |= 0x20  # y6: +64
    elif dy < 0:
        dy = -dy
        if dy & 1:   b[1] |= 0x80; b[1] ^= 0x40  # negative pattern
        # ... (negative uses opposite bit in pair)

    # Encode X displacement similarly
    # ... (X bits are in the other half of each byte)

    # Set command flags in byte 3
    if command == JUMP:
        b[2] |= 0x83  # Jump flag
    elif command == COLOR_CHANGE:
        b[2] |= 0xC3  # Color change flag
    elif command == END:
        b[2] = 0xF3   # End marker

    return bytes(b)
```

> **Note:** The above pseudocode illustrates the concept. For a production implementation, use pyembroidery's `write_dst()` which handles all encoding edge cases correctly.

### 3.5 Coordinate System

DST uses a delta-coordinate system:
- **+X** = needle moves RIGHT
- **-X** = needle moves LEFT
- **+Y** = needle moves AWAY from operator (up in most visualizations)
- **-Y** = needle moves TOWARD operator (down)
- Origin is at the design center (relative to hoop center)
- All coordinates are relative to the previous stitch position

---

## 4. DSB Format and Barudan-Specific Considerations {#dsb-format}

### DSB vs. DST

The DSB (Design Stitch Barudan) format shares the same fundamental stitch-encoding approach as DST but adds Barudan-specific extensions:

| Feature | DST | DSB |
|---------|-----|-----|
| Stitch coordinates | Yes | Yes |
| Color change commands | Yes (index only) | Yes (with color data) |
| Thread color storage | No | Yes (RGB values embedded) |
| Machine-specific instructions | No | Yes (Barudan-optimized) |
| Cross-brand compatibility | Universal | Barudan only |
| Open-source write support | Excellent (pyembroidery) | Read-only (pyembroidery) |
| Public specification | Well-documented | Proprietary / undocumented |

### U03 / FDR-3 Format

Barudan's FDR-3 format (file extension `.U03`) adds:
- Color thumbnail previews on the machine controller display
- Enhanced color management for complex multi-color designs
- Higher stitch precision for certain operations
- Better integration with Barudan's TES digitizing software

This format has essentially zero public documentation and no open-source support. Working with it requires either Barudan's proprietary SDK or extensive reverse engineering.

### Practical Recommendation

Start with DST. It gives you the broadest compatibility and the strongest open-source tooling. DSB support can be added later by:

1. Examining DSB files output by Barudan's TES software (hex dump comparison with equivalent DST files to identify the color-data extension)
2. Studying pyembroidery's `DsbReader.py` source code to understand the read format (then reversing it for writing)
3. Contacting Barudan technical support for format documentation (some vendors provide this under NDA for integration partners)

---

## 5. BNet Software Integration {#bnet-integration}

### What BNet Does

B-NET (and B-NET Pro) is Barudan's production management software that connects up to 100 Barudan machines over a LAN network. Its role in your pipeline is as the final delivery mechanism — it receives embroidery files and dispatches them to machines.

### File Transfer Methods

BNet accepts design files through several channels:

1. **File system / network share:** Drop DST/DSB files into BNet's monitored design directory. This is the simplest integration path for automated workflows.
2. **BNet's HTTP API:** BNet Pro exposes an HTTP-based API for programmatic integration. Documented capabilities include uploading design files, setting thread colors per-design, monitoring machine status and production counts, and job dispatch automation.
3. **USB/media transfer:** Direct loading from USB drives to machines (bypasses BNet for simple setups).

### API Integration (BNet Pro)

BNet Pro's HTTP API supports:
- **Design upload:** Push embroidery files to the BNet server programmatically
- **Thread color assignment:** Set color sequences for DST files (compensating for DST's lack of embedded colors)
- **Production monitoring:** Real-time stitch density tracking, machine status, thread break alerts
- **Job dispatch:** Queue designs to specific machines
- **ERP/WMS integration:** Feed production data into enterprise systems

For your tool, the most relevant API capability is design upload with color assignment — this lets you output DST files (which lack color data) and programmatically assign the correct thread colors through BNet's API, getting the same end result as a DSB file's embedded colors.

### BNet Compatibility Checklist

When generating files for BNet consumption, ensure:
- Files validate as proper DST (512-byte header + 3-byte records + end marker)
- Stitch counts in the header match actual stitch records in the body
- Design extents (+X, -X, +Y, -Y) in the header are accurate
- No single stitch exceeds 12.1mm (auto-split long stitches into jumps)
- Color change commands are properly placed between color sections
- End-of-design marker (`0x00 0x00 0xF3`) is present

---

## 6. Open-Source Libraries {#open-source-libraries}

### 6.1 pyembroidery (Python) — The Foundation Layer

**Repository:** [github.com/EmbroidePy/pyembroidery](https://github.com/EmbroidePy/pyembroidery)
**PyPI:** [pypi.org/project/pyembroidery](https://pypi.org/project/pyembroidery/)
**License:** MIT
**Status:** Actively maintained, mature

**What it does:** Reads 45+ embroidery formats and writes 10+ formats including DST. This is the most complete open-source embroidery I/O library available.

**Core API:**

```python
from pyembroidery import *

# Create a new pattern
pattern = EmbPattern()

# Add thread colors
pattern.add_thread({'color': 0xFF0000, 'name': 'Red'})
pattern.add_thread({'color': 0x0000FF, 'name': 'Blue'})

# Add stitches (absolute coordinates, units = 0.1mm)
pattern.add_stitch_absolute(STITCH, 0, 0)       # First stitch at origin
pattern.add_stitch_absolute(STITCH, 10, 0)       # 1mm to the right
pattern.add_stitch_absolute(STITCH, 10, 10)      # 1mm up
pattern.add_stitch_absolute(COLOR_CHANGE)         # Switch to next color
pattern.add_stitch_absolute(STITCH, 20, 20)
pattern.add_stitch_absolute(END)                  # End design

# Write to DST
write(pattern, "output.dst")

# Or with options
write(pattern, "output.dst", {
    "max_stitch": 121,      # Max stitch length in units
    "max_jump": 121,         # Max jump length
    "tie_on": CONTINGENCY_TIE_ON_THREE_SMALL,
    "tie_off": CONTINGENCY_TIE_OFF_THREE_SMALL,
})
```

**Command constants:**

| Constant | Value | Description |
|----------|-------|-------------|
| `STITCH` | 0 | Normal stitch (needle penetrates fabric) |
| `JUMP` | 1 | Move without stitching |
| `TRIM` | 2 | Cut thread |
| `STOP` | 3 | Pause machine |
| `END` | 4 | End of design |
| `COLOR_CHANGE` | 5 | Switch to next thread color |
| `NEEDLE_SET` | 6 | Set specific needle |
| `SEQUIN_EJECT` | 7 | Sequin placement |
| `SEQUIN_MODE` | 8 | Toggle sequin mode |

**Write settings for DST:**

| Setting | Default | Description |
|---------|---------|-------------|
| `max_stitch` | 121 | Auto-split stitches longer than this (in 0.1mm) |
| `max_jump` | 121 | Auto-split jumps longer than this |
| `tie_on` | varies | Tie-on stitch behavior at stitch start |
| `tie_off` | varies | Tie-off stitch behavior before trim/color change |
| `translate` | (0,0) | Apply X,Y offset to entire design |
| `scale` | 1.0 | Scale factor |
| `rotate` | 0 | Rotation angle |
| `encode` | True | Apply format-specific encoding on write |

**Coordinate system:** pyembroidery uses absolute coordinates internally with +X = right, +Y = down (screen coordinates). When writing DST, it flips Y to match DST's convention (+Y = up/away).

**Key limitation:** pyembroidery is an I/O library only. It does not generate stitches from shapes, images, or vectors. You provide the stitch coordinates; it writes the files.

**Supported write formats:** PES, DST, EXP, JEF, VP3, U01, PEC, XXX, TBF, GCODE, CSV, JSON, PNG, SVG, TXT

### 6.2 Ink/Stitch (Python + Inkscape) — The Algorithm Reference

**Repository:** [github.com/inkstitch/inkstitch](https://github.com/inkstitch/inkstitch)
**Website:** [inkstitch.org](https://inkstitch.org/)
**License:** GPL v2
**Status:** Actively maintained, production-quality

**What it does:** Full embroidery digitizing platform built as an Inkscape extension. Takes SVG vector paths and converts them to embroidery files. This is the most complete open-source auto-digitizing implementation available.

**Why it matters for your project:** Ink/Stitch's source code is the best open-source reference for understanding how auto-fill, satin column, and running stitch algorithms work in practice. Key source files:

- `lib/stitches/auto_fill.py` — The auto-fill algorithm (scanline-based parallel fill with graph-based path optimization)
- `lib/stitches/satin_column.py` — Satin stitch generation from dual-rail paths
- `lib/stitches/running_stitch.py` — Running stitch along paths
- `lib/elements/fill_stitch.py` — Fill stitch element handling

**Auto-fill algorithm overview:**

1. Takes a closed SVG path (polygon, possibly with holes)
2. Generates parallel scan lines at a specified angle and spacing across the polygon
3. Clips scan lines to the polygon boundary (using Shapely geometry operations)
4. Builds a graph connecting the endpoints of adjacent scan lines
5. Uses NetworkX shortest-path algorithms to find an optimal stitching order that minimizes jumps
6. Outputs stitch coordinates following the optimized path

**Satin column algorithm overview:**

1. Takes two parallel paths (rails) defining the satin column boundaries
2. Samples points along each rail at regular intervals
3. Generates zigzag stitches between corresponding points on opposite rails
4. Supports "rungs" (manual cross-connections) for precise control in curved sections
5. Includes auto-routing to connect multiple satin columns with running stitch "underpathing"

**Key dependencies used by Ink/Stitch:**
- **Shapely** — Polygon operations (intersection, buffering, offset)
- **NetworkX** — Graph algorithms for path optimization
- **NumPy** — Numerical computations
- **scikit-image** — Image processing (for bitmap tracing)

### 6.3 stitch-generator (Python) — Clean Algorithmic Primitives

**Repository:** [github.com/bastanja/stitch_generator](https://github.com/bastanja/stitch_generator)
**PyPI:** [pypi.org/project/stitch-generator](https://pypi.org/project/stitch-generator/)
**License:** MIT
**Status:** Maintained, focused scope

**What it does:** Converts basic geometric shapes (lines, Bezier curves, circles) to embroidery stitch patterns. Focuses purely on the stitch generation math — no file I/O (use pyembroidery for that).

**Key concept — the Path:**
```python
from stitch_generator.framework.path import Path
from stitch_generator.shapes.line import line
from stitch_generator.functions.functions_1d import constant

# A Path consists of: position, direction, width at each point
path = Path(
    *line(origin=(-50, 0), to=(50, 0)),  # start and end points
    width=constant(15)                     # constant width of 15 units
)
```

**Available stitch effects:**

| Effect | Description | Input |
|--------|-------------|-------|
| `satin` | Zigzag between path boundaries | Path with width |
| `running_stitch` | Evenly-spaced stitches along path centerline | Path |
| `e_stitch` | E-shaped stitch pattern | Path with width |
| `cross_stitch` | Cross pattern fill | Path with width |
| `motif_stitch` | Repeating motif along path | Path + motif definition |
| `meander` | Space-filling curve within path width | Path with width |

**Output format:** NumPy ndarray of shape `(N, 2)` where N = number of stitches. Each row is `[x, y]` coordinates.

**Integration with pyembroidery:**
```python
from stitch_generator.stitch_effects.path_effects.satin import satin
from stitch_generator.subdivision.subdivide_by_length import regular
from pyembroidery import EmbPattern, STITCH, END, write

# Generate stitch coordinates
stitch_effect = satin(spacing_function=regular(2), line_subdivision=regular(4))
stitches = stitch_effect(path)  # numpy array of [x, y]

# Feed into pyembroidery
pattern = EmbPattern()
pattern.add_thread({'color': 0xFF0000})
for x, y in stitches:
    pattern.add_stitch_absolute(STITCH, x * 10, y * 10)  # convert to 0.1mm
pattern.add_stitch_absolute(END)
write(pattern, "output.dst")
```

### 6.4 PEmbroider (Processing/Java) — Algorithm Reference

**Repository:** [github.com/CreativeInquiry/PEmbroider](https://github.com/CreativeInquiry/PEmbroider)
**License:** GPL v3
**Status:** Maintained, academic project from CMU

**What it does:** Embroidery library for Processing (Java-based creative coding platform). Provides fill, stroke, and hatch algorithms for generating embroidery from programmatic shapes and images.

**Fill/hatch modes available:**

| Mode | Description | Stability |
|------|-------------|-----------|
| `PARALLEL` | Parallel lines at specified angle and spacing | Solid |
| `CONCENTRIC` | Nested inset shapes progressively shrinking | Solid |
| `SATIN` | Satin column stitches | Solid |
| `SPIRAL` | Spiral patterns radiating inward | Buggy |
| `PERLIN` | Organic flowing patterns using Perlin noise | Experimental |
| `CROSS` | Cross-hatching (two intersecting parallel sets) | Stable |
| `VECFIELD` | Follows custom vector fields | Experimental |
| `DRUNK` | Random walk patterns | Experimental |

**Stroke modes:**

| Mode | Description |
|------|-------------|
| `PERPENDICULAR` | Offset strokes perpendicular to edges |
| `TANGENT` | Strokes following edge tangent direction |

**Why it matters:** PEmbroider's algorithms are well-documented in its API reference and implemented in a readable style. Even though it's Java, the math translates directly to Python/JavaScript. The PARALLEL and CONCENTRIC algorithms are particularly clean references for implementing your own fill routines.

### 6.5 libembroidery (C) — Low-Level Alternative

**Repository:** [github.com/Embroidermodder/libembroidery](https://github.com/Embroidermodder/libembroidery)
**Website:** [libembroidery.org](https://www.libembroidery.org/)
**License:** zlib (very permissive)
**Status:** Alpha, under active development

**What it does:** Single-header C library for reading/writing 45+ embroidery formats. Part of the Embroidermodder project. Includes both format I/O and some geometry/stitch-generation routines.

**When to use it:** If you need maximum performance (C speed), minimal dependencies (single header file), or are building in a compiled language. For Python-based projects, pyembroidery is the better choice.

### 6.6 Library Comparison Matrix

| Capability | pyembroidery | Ink/Stitch | stitch-generator | PEmbroider | libembroidery |
|-----------|-------------|-----------|-----------------|-----------|--------------|
| **Language** | Python | Python | Python | Java | C |
| **DST Write** | Yes | Via pyembroidery | No (coordinates only) | Via writer | Yes |
| **DSB Write** | No (read only) | No | No | No | Unclear |
| **Auto-fill** | No | Yes | No | Yes | Partial |
| **Satin stitch** | No | Yes | Yes | Yes | Partial |
| **Running stitch** | No | Yes | Yes | Yes | Partial |
| **Image input** | No | Via Inkscape | No | Yes | No |
| **Path optimization** | No | Yes (NetworkX) | No | Yes | Partial |
| **License** | MIT | GPL v2 | MIT | GPL v3 | zlib |

---

## 7. The Image-to-Embroidery Pipeline {#pipeline}

Converting a raster image (PNG, JPG) to an embroidery file requires a multi-stage pipeline. No single open-source library handles this end-to-end. You need to build it by composing several algorithms and libraries.

### 7.1 Pipeline Overview

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│ 1. Image     │────▶│ 2. Color     │────▶│ 3. Vectorize  │────▶│ 4. Classify  │
│ Preprocessing│     │ Quantization │     │ Regions       │     │ Stitch Types │
└─────────────┘     └──────────────┘     └───────────────┘     └──────────────┘
                                                                      │
┌─────────────┐     ┌──────────────┐     ┌───────────────┐           │
│ 8. Write    │◀────│ 7. Path      │◀────│ 6. Apply      │◀──────────┘
│ DST File    │     │ Optimization │     │ Compensation  │
└─────────────┘     └──────────────┘     └───────────────┘
                                                ▲
                                         ┌──────┴──────┐
                                         │ 5. Generate │
                                         │ Stitch Paths│
                                         └─────────────┘
```

### 7.2 Stage 1: Image Preprocessing

**Goal:** Clean and normalize the input image for reliable segmentation.

**Operations:**
- Resize to target embroidery dimensions (considering DPI → mm conversion)
- Remove background (alpha channel detection or background subtraction)
- Denoise (Gaussian blur or bilateral filter to reduce artifacts)
- Edge enhancement (for preserving important boundaries)

**Libraries:** OpenCV (`cv2`), Pillow (`PIL`), scikit-image

```python
import cv2
import numpy as np

def preprocess_image(image_path, target_width_mm, target_height_mm, dpi=300):
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    # Convert to target physical size
    px_per_mm = dpi / 25.4
    target_w_px = int(target_width_mm * px_per_mm)
    target_h_px = int(target_height_mm * px_per_mm)
    img = cv2.resize(img, (target_w_px, target_h_px))

    # Denoise
    img = cv2.bilateralFilter(img, 9, 75, 75)

    return img
```

### 7.3 Stage 2: Color Quantization

**Goal:** Reduce the image to a limited number of colors that correspond to available thread colors. Embroidery typically uses 1-15 thread colors per design.

**Algorithms:**

1. **K-Means Clustering:** Cluster pixel colors in RGB/LAB space. K = desired number of thread colors.
2. **Median Cut:** Recursively divide the color space by the axis with greatest range.
3. **Thread-Color Matching:** After quantization, map each cluster center to the nearest available thread color from a thread palette (e.g., Madeira, Isacord, Robison-Anton).

```python
from sklearn.cluster import KMeans

def quantize_colors(img, n_colors=8):
    # Reshape to pixel list
    pixels = img.reshape(-1, 3).astype(np.float32)

    # K-means in LAB color space (better perceptual uniformity)
    lab_pixels = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    kmeans = KMeans(n_clusters=n_colors, random_state=42)
    labels = kmeans.fit_predict(lab_pixels)

    # Map back to BGR centers
    centers_lab = kmeans.cluster_centers_.astype(np.uint8)
    centers_bgr = cv2.cvtColor(
        centers_lab.reshape(1, -1, 3), cv2.COLOR_LAB2BGR
    ).reshape(-1, 3)

    # Create quantized image
    quantized = centers_bgr[labels].reshape(img.shape)

    return quantized, labels.reshape(img.shape[:2]), centers_bgr
```

### 7.4 Stage 3: Vectorization (Region Extraction)

**Goal:** Convert each color region from a raster mask into vector polygons (outlines).

**Algorithms:**

1. **Contour Tracing:** For each color, create a binary mask and find contours using OpenCV's `findContours` (implements the Suzuki-Abe algorithm).
2. **Contour Simplification:** Reduce polygon complexity using the Douglas-Peucker algorithm (`cv2.approxPolyDP`).
3. **Polygon Cleanup:** Remove small regions (noise), fill holes below a minimum size, smooth jagged edges.

```python
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

def extract_regions(label_map, n_colors):
    regions = []
    for color_idx in range(n_colors):
        mask = (label_map == color_idx).astype(np.uint8) * 255
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )

        polygons = []
        for i, contour in enumerate(contours):
            if len(contour) < 3:
                continue
            simplified = cv2.approxPolyDP(contour, epsilon=1.0, closed=True)
            coords = [(p[0][0], p[0][1]) for p in simplified]
            if len(coords) >= 3:
                poly = Polygon(coords)
                if poly.is_valid and poly.area > 10:  # min area filter
                    polygons.append(poly)

        if polygons:
            merged = unary_union(polygons)
            regions.append({
                'color_index': color_idx,
                'geometry': merged
            })
    return regions
```

### 7.5 Stage 4: Stitch Type Classification

**Goal:** For each vector region, determine the appropriate stitch type based on the region's geometry.

**Decision rules:**

| Region Characteristic | Stitch Type | Reasoning |
|----------------------|-------------|-----------|
| Thin, elongated (width < 3mm) | Satin stitch | Perpendicular zigzag fills narrow columns cleanly |
| Small area (< 4mm²) | Running stitch outline | Too small to fill meaningfully |
| Large area (> ~20mm²) | Fill stitch (parallel hatching) | Efficient coverage of broad areas |
| Medium area | Fill stitch or satin | Depends on aspect ratio |
| Single-pixel-width line | Running stitch | Follows the path directly |
| Text / lettering | Satin for strokes, fill for large letters | Standard digitizing practice |

**Implementation approach:**
```python
def classify_stitch_type(polygon):
    area = polygon.area
    bounds = polygon.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    aspect = max(width, height) / max(min(width, height), 0.01)

    # Minimum bounding rectangle width
    min_width = estimate_minimum_width(polygon)

    if min_width < 30:       # < 3mm (in 0.1mm units)
        return 'satin'
    elif area < 400:          # < 4mm²
        return 'running'
    else:
        return 'fill'
```

### 7.6 Stage 5-6: Stitch Generation (see next section)

### 7.7 Stage 7: Path Optimization

**Goal:** Determine the order in which regions are stitched to minimize jump stitches and thread changes.

This is effectively a **Traveling Salesman Problem (TSP)** variant — each region has a start and end point, and you want to order them to minimize total travel distance between regions.

**Algorithms:**
- **Nearest-neighbor heuristic:** Start with any region; always stitch the nearest unstitched region next. O(n²), simple, gives ~80% optimal results.
- **2-opt improvement:** After initial ordering, iteratively reverse subsequences to find shorter total paths.
- **Color-grouped ordering:** Stitch all regions of one color before changing threads. Within each color group, apply TSP optimization.

### 7.8 Stage 8: File Writing

Use pyembroidery to assemble the final file:

```python
from pyembroidery import *

def assemble_design(stitch_groups, thread_colors):
    pattern = EmbPattern()

    for i, color in enumerate(thread_colors):
        pattern.add_thread({'color': color})

    current_color = 0
    for group in stitch_groups:
        if group['color_index'] != current_color:
            pattern.add_command(COLOR_CHANGE)
            current_color = group['color_index']

        first = True
        for x, y in group['stitches']:
            if first:
                pattern.add_stitch_absolute(JUMP, x, y)
                first = False
            else:
                pattern.add_stitch_absolute(STITCH, x, y)

        pattern.add_command(TRIM)

    pattern.add_command(END)
    write(pattern, "output.dst")
```

---

## 8. Core Algorithms: Stitch Generation {#stitch-generation-algorithms}

### 8.1 Fill Stitch (Parallel Hatching)

Fill stitch covers large areas with rows of parallel stitches. This is the most common stitch type and the most algorithmically interesting.

**The Scanline Fill Algorithm:**

1. **Define scan direction:** Choose a fill angle (e.g., 45 degrees)
2. **Generate scan lines:** Create parallel lines across the polygon at the chosen angle, spaced by the desired row spacing (typically 0.4mm - 0.6mm apart, which translates to 4-6 units in DST's 0.1mm resolution)
3. **Clip to polygon:** For each scan line, compute intersections with the polygon boundary using Shapely's `intersection()` method. This produces line segments inside the polygon.
4. **Generate stitches along segments:** Place stitches along each segment at the desired stitch length (typically 2-4mm)
5. **Connect segments:** The segments must be connected in a continuous path to minimize jumps. This is where the algorithm gets complex.

**Segment Connection Strategies:**

| Strategy | Description | Quality |
|----------|-------------|---------|
| **Alternating direction** | Zigzag: stitch left→right on one row, right→left on the next | Good — eliminates most jumps |
| **Graph-based (Ink/Stitch)** | Build a graph of segment endpoints; find shortest path connecting all segments | Best — minimizes total travel |
| **Nearest-endpoint** | After finishing a segment, start the nearest segment | Simple, often adequate |

**Stagger/Offset:** To avoid visible "laddering" (alignment of stitch endpoints across rows), offset each row by a fraction of the stitch length. A common pattern is to stagger by 1/4 of stitch length on alternating rows.

```python
from shapely.geometry import LineString, MultiLineString, box
from shapely.affinity import rotate
import numpy as np

def generate_fill_stitches(polygon, angle_deg=45, row_spacing=4.0, stitch_length=30.0):
    """
    Generate fill stitches for a polygon.

    Args:
        polygon: Shapely Polygon
        angle_deg: Fill angle in degrees
        row_spacing: Distance between rows (0.1mm units)
        stitch_length: Max stitch length (0.1mm units)

    Returns:
        List of (x, y) stitch coordinates
    """
    # Rotate polygon to align scan lines with X axis
    rotated = rotate(polygon, -angle_deg, origin='centroid')
    minx, miny, maxx, maxy = rotated.bounds

    stitches = []
    row_idx = 0
    y = miny + row_spacing / 2

    while y <= maxy:
        # Create scan line across full width
        scan_line = LineString([(minx - 10, y), (maxx + 10, y)])
        intersection = rotated.intersection(scan_line)

        if intersection.is_empty:
            y += row_spacing
            row_idx += 1
            continue

        # Get line segments
        segments = []
        if isinstance(intersection, LineString):
            segments = [intersection]
        elif isinstance(intersection, MultiLineString):
            segments = list(intersection.geoms)

        # Alternate direction for zigzag
        if row_idx % 2 == 1:
            segments = segments[::-1]

        for seg in segments:
            coords = list(seg.coords)
            if row_idx % 2 == 1:
                coords = coords[::-1]

            # Place stitches along segment
            line = LineString(coords)
            length = line.length

            # Stagger offset
            offset = (row_idx % 4) * (stitch_length / 4)

            dist = offset
            while dist < length:
                pt = line.interpolate(dist)
                stitches.append((pt.x, pt.y))
                dist += stitch_length

            # Always include endpoint
            end = line.interpolate(length)
            stitches.append((end.x, end.y))

        y += row_spacing
        row_idx += 1

    # Rotate stitches back to original orientation
    angle_rad = np.radians(angle_deg)
    cx, cy = polygon.centroid.coords[0]
    rotated_stitches = []
    rcx, rcy = rotate(polygon, -angle_deg, origin='centroid').centroid.coords[0]

    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    for x, y in stitches:
        dx, dy = x - rcx, y - rcy
        rx = dx * cos_a - dy * sin_a + cx
        ry = dx * sin_a + dy * cos_a + cy
        rotated_stitches.append((rx, ry))

    return rotated_stitches
```

### 8.2 Satin Stitch

Satin stitch creates a column of zigzag stitches between two parallel edges. Used for borders, text, and narrow features.

**Algorithm:**

1. **Input:** Two rail paths (left and right boundaries of the column)
2. **Parameterize rails:** Sample both rails at equal intervals of parameter `t` from 0.0 to 1.0
3. **Generate zigzag:** Alternate between points on the left rail and corresponding points on the right rail
4. **Handle width variation:** If the column width varies, the corresponding points should be matched by parameter (not by distance), which naturally handles tapering and curved columns

```python
def generate_satin_stitches(left_rail, right_rail, density=4.0):
    """
    Generate satin stitches between two rail paths.

    Args:
        left_rail: List of (x, y) points defining the left boundary
        right_rail: List of (x, y) points defining the right boundary
        density: Stitches per mm along the rail

    Returns:
        List of (x, y) stitch coordinates (zigzag pattern)
    """
    left_line = LineString(left_rail)
    right_line = LineString(right_rail)

    # Calculate spacing along the longer rail
    length = max(left_line.length, right_line.length)
    n_stitches = int(length * density / 10)  # density per mm, length in 0.1mm

    stitches = []
    for i in range(n_stitches):
        t = i / max(n_stitches - 1, 1)

        left_pt = left_line.interpolate(t, normalized=True)
        right_pt = right_line.interpolate(t, normalized=True)

        if i % 2 == 0:
            stitches.append((left_pt.x, left_pt.y))
        else:
            stitches.append((right_pt.x, right_pt.y))

    return stitches
```

**For creating satin columns from a single centerline path (common when vectorizing from images):**

1. Compute the offset curves on both sides of the centerline (Shapely's `parallel_offset` or `buffer`)
2. Use the offset curves as the two rails
3. Apply the zigzag algorithm above

### 8.3 Running Stitch

The simplest stitch type. Places evenly-spaced stitch points along a path.

```python
def generate_running_stitches(path_points, stitch_length=20.0):
    """
    Generate running stitches along a path.

    Args:
        path_points: List of (x, y) points defining the path
        stitch_length: Distance between stitches (0.1mm units)

    Returns:
        List of (x, y) stitch coordinates
    """
    line = LineString(path_points)
    length = line.length

    stitches = []
    dist = 0
    while dist <= length:
        pt = line.interpolate(dist)
        stitches.append((pt.x, pt.y))
        dist += stitch_length

    # Always include the endpoint
    end = line.interpolate(length)
    if stitches[-1] != (end.x, end.y):
        stitches.append((end.x, end.y))

    return stitches
```

### 8.4 Underlay Stitches

Underlay is a foundation layer stitched before the visible top stitches. It serves three critical purposes:

1. **Fabric stabilization:** Prevents the fabric from stretching or distorting under the top stitches
2. **Surface preparation:** Creates a raised platform that makes top stitches sit higher and look better
3. **Pull compensation support:** Helps maintain shape against the pulling forces of dense stitching

**Common underlay types:**

| Type | Description | Used under |
|------|-------------|-----------|
| **Center walk** | Single running stitch along the centerline | Satin columns (narrow) |
| **Edge walk** | Running stitch along both edges | Satin columns (medium-wide) |
| **Zigzag underlay** | Light zigzag at wider spacing than top layer | Satin columns (wide) |
| **Fill underlay** | Sparse fill at ~90° to top fill direction | Fill stitch areas |
| **Double fill underlay** | Two layers of sparse fill at different angles | Dense fill areas on stretchy fabrics |

**Implementation:** Generate underlay stitches using the same algorithms as top stitches, but with wider spacing (typically 2x the top layer spacing), running perpendicular to the top layer direction, and placed as the first stitches in each color region before the visible stitches.

---

## 9. Physical Compensation Algorithms {#physical-compensation}

When a needle pushes thread into fabric, the physical interaction between thread, fabric, and machine creates predictable distortions. Compensation algorithms pre-distort the digital design so that the physical output matches the intended design.

### 9.1 Pull Compensation

**The problem:** Dense stitching (especially satin stitch) pulls fabric inward, making columns narrower than designed.

**The solution:** Widen the digital design by an amount that compensates for the expected pull. When the fabric pulls in, the result matches the original intended dimensions.

**Implementation:**
```python
def apply_pull_compensation(polygon, compensation_mm=0.2):
    """
    Expand a polygon to compensate for pull distortion.

    Args:
        polygon: Shapely Polygon
        compensation_mm: Amount to expand (in mm)

    Returns:
        Expanded Shapely Polygon
    """
    compensation_units = compensation_mm * 10  # Convert to 0.1mm
    return polygon.buffer(compensation_units, join_style=2)  # mitre join
```

**Typical compensation values:**
- Light woven fabric: 0.1-0.2mm per side
- Medium knit: 0.2-0.3mm per side
- Heavy stretch/terry: 0.3-0.5mm per side

**Note:** There is no universal formula. Compensation depends on fabric type, stitch density, stabilizer used, and machine tension. Professional digitizers develop this intuition through experience. For automated conversion, a configurable parameter with sensible defaults is the best approach.

### 9.2 Push Compensation

**The problem:** At the ends of satin columns, stitches push outward, making the ends wider/longer than intended.

**The solution:** Shorten the ends of the digital design to compensate. This is harder to automate than pull compensation because it is highly dependent on column width, stitch density, and fabric.

**Implementation approach:** Indent the endpoints of satin columns by a small amount (typically 0.1-0.3mm) proportional to the column width.

### 9.3 Density Management

**The problem:** Too-dense stitching causes thread breaks, needle breaks, and fabric puckering. Too-sparse stitching shows the fabric through the design.

**Guidelines for stitch density:**

| Stitch Type | Row Spacing | Notes |
|------------|-------------|-------|
| Fill stitch | 0.4mm - 0.5mm (4-5 units) | Standard for most fabrics |
| Satin stitch | Auto (width-dependent) | Width up to ~12mm before requiring split |
| Running stitch | 2-3mm (20-30 units) | Between stitches along path |
| Underlay fill | 0.8mm - 1.2mm (8-12 units) | Wider spacing than top layer |

---

## 10. Path Optimization {#path-optimization}

### 10.1 Intra-Region Optimization

Within a single fill region, the challenge is connecting scan line segments into a continuous path with minimal jumps.

**Ink/Stitch's approach (state of the art for open source):**

1. Build a graph where nodes are segment endpoints
2. Add edges between endpoints that can be connected by traveling along the polygon boundary (running stitch under subsequent top stitches)
3. Find the Eulerian path or minimum-cost path that visits all segments
4. This uses NetworkX's shortest path algorithms

### 10.2 Inter-Region Optimization (Stitching Order)

**Color-first grouping:** Group all regions by thread color. Stitch all regions of one color before changing to the next. Within each color group, optimize the order using nearest-neighbor or 2-opt TSP heuristic.

**Minimizing color changes:** If the design has many small regions of different colors, reordering can significantly reduce color changes. Each color change takes 5-30 seconds on the machine (operator intervention for manual thread change or automatic needle change).

### 10.3 Trim and Jump Optimization

**Rules for DST:**
- If the distance to the next stitch area is < ~3mm: use a direct jump (no trim needed)
- If > ~3mm: use a trim followed by jump(s) to the new area
- Many machines auto-trim after 3-5 consecutive jump stitches. You can exploit this by encoding multiple jumps instead of explicit trims for cleaner results on specific machines.

---

## 11. Adjacent Opportunities {#adjacent-opportunities}

### 11.1 SVG-to-Embroidery (High Relevance)

Instead of raster images, accepting SVG vector input dramatically simplifies the pipeline — you skip stages 1-3 (preprocessing, quantization, vectorization) entirely, since SVG paths are already vector polygons. Many logos and designs exist as SVG files, making this a high-value secondary input format.

**Signal strength:** HIGH — This reuses 80% of your fill/satin/running stitch algorithms with much higher output quality.

**Next step:** Study Ink/Stitch's SVG parsing pipeline as a reference implementation.

### 11.2 Applique Support (Medium Relevance)

Applique is a technique where fabric pieces are attached to the base garment using embroidered outlines rather than filling entire regions with stitches. This dramatically reduces stitch count (and thus production time) for large solid-color areas. Many commercial designs use applique for areas larger than ~25mm².

**Signal strength:** MEDIUM — Adds a valuable production technique to your tool.

**Next step:** Research applique stitch patterns (placement line + tack-down + satin border).

### 11.3 Lettering Engine (High Relevance)

Text embroidery is one of the most common commercial applications (names, monograms, logos with text). A dedicated lettering engine that generates satin-column letters from font data would be a high-value feature.

**Signal strength:** HIGH — Every embroidery shop needs text capabilities.

**Next step:** Study how TrueType font outlines can be converted to satin column pairs.

---

## 12. Competing Perspectives and Counterarguments {#counterarguments}

### "Auto-digitizing never produces professional-quality results"

This is the strongest counterargument against building an automated image-to-embroidery tool. Experienced digitizers consistently report that auto-digitized designs require significant manual cleanup — particularly around stitch direction optimization, density variations, and pull compensation for specific fabrics.

**Why this matters for your project:** Your tool will likely produce designs that are functional but not production-quality without manual refinement. This is acceptable for many use cases (prototyping, simple logos, non-critical applications) but may not satisfy customers who compare against hand-digitized work.

**Mitigation:** Position the tool as a first-pass digitizer that produces a solid starting point, then allow manual adjustment of stitch parameters, regions, and paths. The tool's value is in automating the tedious 80% so the operator can focus on the creative 20%.

### "DST is good enough; DSB adds marginal value"

Some practitioners argue that since color assignment takes only seconds per design, the lack of embedded colors in DST is not a meaningful limitation, especially when BNet's API can handle color assignment programmatically. The counterpoint is that for high-volume production (hundreds of designs per day), embedded colors in DSB reduce error rates and save cumulative operator time.

### "pyembroidery handles everything you need"

pyembroidery is an excellent I/O library but it is explicitly *not* a digitizing engine. The gap between "write stitch coordinates to DST" and "convert an image to stitch coordinates" is where all the algorithmic complexity lives. pyembroidery is a necessary foundation layer, but it represents perhaps 10% of the total engineering effort for an image-to-embroidery tool.

---

## 13. Decision Points {#decision-points}

### Decision 1: Primary Output Format

- **Option A: DST only** → Maximum compatibility, excellent library support, requires external color assignment (via BNet API or manual). Fastest path to a working product.
- **Option B: DST + DSB** → Native Barudan experience with embedded colors, but DSB writing must be reverse-engineered or obtained from Barudan under NDA. Adds significant development time.
- **Recommendation:** Start with Option A. Add DSB later based on production needs.

### Decision 2: Programming Language

- **Option A: Python** → Best library ecosystem (pyembroidery, Shapely, OpenCV, NumPy, scikit-image, NetworkX all native). Fastest development time.
- **Option B: JavaScript/TypeScript** → Better for web-based tools, but limited embroidery library support. Would need Python backend or WASM compilation.
- **Option C: C/C++** → Maximum performance (libembroidery), but slowest development time.
- **Recommendation:** Python for the digitizing engine and file generation, with optional web UI in JS that calls the Python backend.

### Decision 3: Build vs. Use Ink/Stitch

- **Option A: Use Ink/Stitch as a subprocess** → Call Ink/Stitch's Python modules directly for fill/satin generation. Leverages years of algorithm development. GPL v2 license requires your tool to be GPL-compatible if you distribute it.
- **Option B: Build from scratch using Ink/Stitch as reference** → Study Ink/Stitch's algorithms, reimplement in your own codebase. More work, but avoids GPL licensing constraints and gives full control.
- **Option C: Build on stitch-generator + pyembroidery** → Use MIT-licensed libraries as the foundation, build the pipeline yourself. Maximum flexibility, MIT licensing.
- **Recommendation:** Option C for the foundation (MIT licensing, clean API), with Option B for advanced algorithms (study Ink/Stitch's auto-fill graph optimization).

---

## 14. Horizon: Worth Knowing About {#horizon}

**AI/ML-based digitizing:** Several companies (Wilcom, Hatch, Pulse) are integrating neural networks for automatic stitch type classification and density optimization. Academic research on directionality-aware embroidery patterns (Zhenyuan et al., 2023, Computer Graphics Forum) shows that ML can optimize stitch direction fields for better visual quality. This is the future of auto-digitizing but is not yet available in open-source.

**3D embroidery / puff embroidery:** Emerging technique using foam layers under stitching to create raised/3D effects. Requires specific stitch settings (longer stitch length to clear foam, specific density ranges). Worth planning for in your architecture even if not implementing immediately.

**Sequin attachment:** Some Barudan machines support automatic sequin placement. DST supports sequin commands (via pyembroidery's SEQUIN_EJECT). Niche but high-value for fashion embroidery.

**Thread-break detection integration:** BNet Pro's API reports thread breaks in real-time. A feedback loop that adjusts density parameters based on thread-break rates per design would be a valuable production optimization feature.

**GCODE output:** pyembroidery supports writing GCODE format, which opens the door to CNC embroidery machines and maker-space equipment beyond traditional commercial machines.

---

## 15. Sources and Confidence {#sources}

### Primary Sources Used

**File Format Specifications:**
- [EduTech Wiki - Embroidery format DST](https://edutechwiki.unige.ch/en/Embroidery_format_DST) — Most comprehensive public DST specification. Confidence: HIGH
- [KDE Community Wiki - Tajima Ternary](https://community.kde.org/Projects/Liberty/File_Formats/Tajima_Ternary) — Detailed ternary encoding specification. Confidence: HIGH
- [Achatina.de DST Technical Reference](http://www.achatina.de/sewing/main/TECHNICL.HTM) — Original reverse-engineering of DST format. Confidence: HIGH (historical reference)

**Open-Source Libraries:**
- [pyembroidery GitHub](https://github.com/EmbroidePy/pyembroidery) — Primary embroidery I/O library. Confidence: HIGH (active, well-tested)
- [pyembroidery PyPI](https://pypi.org/project/pyembroidery/) — Latest version and documentation. Confidence: HIGH
- [Ink/Stitch GitHub](https://github.com/inkstitch/inkstitch) — Open-source digitizing platform. Confidence: HIGH
- [Ink/Stitch Documentation](https://inkstitch.org/docs/) — Stitch type documentation. Confidence: HIGH
- [stitch-generator GitHub](https://github.com/bastanja/stitch_generator) — Stitch generation library. Confidence: HIGH
- [stitch-generator PyPI](https://pypi.org/project/stitch-generator/) — Package documentation. Confidence: HIGH
- [PEmbroider GitHub](https://github.com/CreativeInquiry/PEmbroider) — Processing embroidery library. Confidence: HIGH
- [PEmbroider API](https://github.com/CreativeInquiry/PEmbroider/blob/master/API.md) — Algorithm documentation. Confidence: HIGH
- [libembroidery GitHub](https://github.com/Embroidermodder/libembroidery) — C embroidery library. Confidence: MEDIUM (alpha status)

**Barudan / BNet:**
- [Barudan B-NET Product Page](https://barudan.co.jp/en/post-product/product28/) — Official BNet features. Confidence: HIGH
- [Barudan America Software](https://www.barudanamerica.com/software/) — Software overview. Confidence: HIGH
- [MagneticHoop - Barudan Software Guide](https://www.magnetichoop.com/blogs/news/barudan-software-guide-mastering-digitizing-updates-and-machine-integration) — BNet integration details. Confidence: MEDIUM (third-party)
- [MaggieFrameStore - Barudan File Formats](https://maggieframestore.com/blogs/maggieframe-news/barudan-file-formats-demystified-compatibility-conversion-optimization-2025-guide) — Format comparison. Confidence: MEDIUM

**Algorithms & Research:**
- [Ink/Stitch Fill Stitch Docs](https://inkstitch.org/docs/stitches/fill-stitch/) — Auto-fill algorithm description. Confidence: HIGH
- [Ink/Stitch Satin Column Docs](https://inkstitch.org/docs/stitches/satin-column/) — Satin algorithm description. Confidence: HIGH
- [Ink/Stitch Routing Tutorial](https://inkstitch.org/tutorials/routing/) — Path optimization. Confidence: HIGH
- [Google Patents US6587745B1 - Curved Line Fill Stitching](https://patents.google.com/patent/US6587745) — Fill algorithm patent. Confidence: HIGH
- [ScienceDirect - Spiral Fashion Embroidery Path Generation](https://www.sciencedirect.com/science/article/abs/pii/S0010448505001636) — Academic reference. Confidence: HIGH
- [Zhenyuan et al., 2023 - Directionality-Aware Embroidery Patterns](https://onlinelibrary.wiley.com/doi/10.1111/cgf.14770) — Academic reference. Confidence: HIGH
- [Embroidery Legacy - Push & Pull Compensation](https://embroiderylegacy.com/push-pull-compensation-embroidery-digitizing/) — Practitioner resource. Confidence: MEDIUM
- [Embroidery Legacy - Underlay Stitches](https://embroiderylegacy.com/embroidery-digitizing-underlay-digitizing/) — Practitioner resource. Confidence: MEDIUM

### Significant Information Gaps

1. **DSB binary format specification:** No public documentation exists. The format would need to be reverse-engineered from sample files or obtained from Barudan. Gap impact: Cannot write native Barudan files without this.

2. **BNet Pro API documentation:** The API exists and supports HTTP communication, but no public API reference or OpenAPI spec was found. Contact Barudan directly or access through a BNet Pro license. Gap impact: Limits automated BNet integration.

3. **Barudan U03/FDR-3 format:** Completely undocumented publicly. No open-source support. Gap impact: Cannot target Barudan's most advanced format.

4. **Empirical pull compensation data:** No published, quantitative compensation tables by fabric type. Professional digitizers develop this knowledge through experience. Gap impact: Compensation must be user-configurable rather than automatic.

### Overall Confidence Rating: **MEDIUM-HIGH**

The core technology (DST format, libraries, algorithms) is well-documented and has mature open-source implementations. The gaps are primarily around Barudan-proprietary formats and physical compensation parameters, which are solvable through either direct Barudan engagement or iterative testing with actual machines.

---
---

# Part 2: Embroidery Visualization, Simulation & Thread/Fabric Cataloguing

---

## TL;DR — Visualization

Realistic embroidery preview requires rendering individual stitches as oriented capsule shapes with anisotropic thread shading (the Kajiya-Kay fiber model adapted from hair rendering). The rendering pipeline has three tiers of increasing fidelity: 2D flat stitch diagrams (fast, useful for proofing), 2.5D texture-space rendering with per-stitch lighting (production quality, used by commercial software), and full 3D geometric thread modeling (research-quality, computationally expensive). For thread and fabric cataloguing, no manufacturer offers a public API — but comprehensive RGB color data exists in downloadable PDF/CSV form for all major brands (Isacord, Madeira, Robison-Anton, Sulky, Gunold), and pyembroidery's `EmbThread` object can store manufacturer, catalog number, and color data. Your best strategy is to build a JSON-based thread catalogue by scraping the publicly available RGB data from manufacturer PDFs, then map thread selections to your rendering pipeline using Delta-E color matching in CIELAB space.

---

## 16. Embroidery Visualization: Rendering Approaches {#visualization}

### 16.1 The Three Tiers of Stitch Rendering

Embroidery visualization spans a wide quality spectrum. The right tier depends on your use case — quick proofing vs. customer-facing previews vs. photorealistic mockups.

#### Tier 1: 2D Flat/Wireframe Rendering

**What it is:** Render each stitch as a colored line segment between its start and end coordinates. Jumps rendered as dashed lines, trims not rendered.

**Quality:** Low — looks like a technical diagram, not embroidery. Useful for digitizer proofing, stitch path inspection, and debugging.

**Implementation:** This is what pyembroidery's built-in PNG and SVG writers produce. pyembroidery can write directly to PNG (rasterized stitch paths) and SVG (vector stitch paths). Ink/Stitch's simulator also falls into this tier — it animates stitch-by-stitch placement but renders simple line segments.

```python
from pyembroidery import *

pattern = read("design.dst")
# Write flat visualization
write(pattern, "preview.png")   # Raster preview
write(pattern, "preview.svg")   # Vector preview
```

**Pros:** Trivial to implement, fast, works in any viewer.
**Cons:** Doesn't show how the design will actually look when stitched. No thread texture, no fabric interaction, no depth.

#### Tier 2: 2.5D Texture-Space Rendering (Production Quality)

**What it is:** Each stitch is rendered as an oriented capsule (rounded rectangle) with width matching the thread diameter (~0.4mm for 40wt thread), positioned and rotated according to the stitch direction. A lighting model simulates thread sheen and directional highlights. Stitches are rendered in layers to capture overlapping (the "2.5D" aspect — stitches have draw order but not true 3D geometry).

**This is the industry standard for commercial embroidery software previews** — what Wilcom, Hatch, Pulse, and Tajima DG/ML use to show customers "what it will look like."

**The algorithm (from Chen, McCool et al., Graphics Interface 2012):**

1. **Capture lighting environment** on the surface of the target object (or use a fixed lighting rig for flat previews)
2. **Render stitches in texture space** — each stitch drawn as a textured capsule at the correct position, angle, and scale
3. **Apply per-stitch lighting** using an anisotropic BRDF suitable for thread fibers (see Section 16.2)
4. **Build texture pyramid** from the rendered stitch texture for scale-dependent antialiasing
5. **Composite onto fabric texture** — blend the stitch texture over a fabric substrate image

**Implementation approach for your project:**

```python
# Conceptual pipeline for 2.5D stitch rendering
import numpy as np
from PIL import Image, ImageDraw

def render_stitch_preview(stitches, thread_colors, canvas_size, fabric_texture=None):
    """
    Render a 2.5D embroidery preview.

    Each stitch is drawn as an oriented capsule with thread-like shading.
    """
    # Scale: 1 pixel = 0.1mm (matches DST resolution) or adjust for DPI
    scale = 3  # pixels per 0.1mm unit (gives ~762 DPI)
    width, height = canvas_size[0] * scale, canvas_size[1] * scale

    # Start with fabric texture or solid background
    if fabric_texture:
        canvas = fabric_texture.resize((width, height))
    else:
        canvas = Image.new('RGB', (width, height), (240, 235, 220))  # Off-white

    draw = ImageDraw.Draw(canvas)

    thread_width = int(0.4 * 10 * scale)  # 0.4mm thread ≈ 4 units * scale

    current_color_idx = 0
    for i, stitch in enumerate(stitches):
        if stitch['command'] == 'COLOR_CHANGE':
            current_color_idx += 1
            continue
        if stitch['command'] in ('JUMP', 'TRIM', 'END'):
            continue

        x1, y1 = stitch['x1'] * scale, stitch['y1'] * scale
        x2, y2 = stitch['x2'] * scale, stitch['y2'] * scale

        color = thread_colors[current_color_idx % len(thread_colors)]

        # Draw stitch as a thick line with rounded caps (capsule shape)
        draw.line([(x1, y1), (x2, y2)],
                  fill=color, width=thread_width)

        # Add highlight along thread direction for sheen effect
        highlight_color = brighten(color, 0.3)
        draw.line([(x1, y1), (x2, y2)],
                  fill=highlight_color, width=max(1, thread_width // 4))

    return canvas
```

**Pros:** Fast enough for real-time preview. Produces results that closely match the stitched output. Customers can approve designs from this.
**Cons:** Doesn't capture true 3D thread interaction (overlap, shadow, pile). Requires tuning the highlight model per thread type.

#### Tier 3: Full 3D Geometric Thread Rendering

**What it is:** Model each thread segment as a 3D cylinder (or tube with circular cross-section), positioned in 3D space with actual height based on stitch layering order. Ray-trace or rasterize with physically-based materials.

**Reference implementations:**

- **POV-Ray Thread Project** ([dnyarri.github.io/povthread.html](https://dnyarri.github.io/povthread.html)) — Open-source POV-Ray scripts that model individual thread segments as 3D objects. The "Stitch" program simulates cross-stitch by placing 3D thread objects colored from a source image. Includes Perlin noise distortion to simulate fabric deformation, making the too-regular digital output look more natural. The "Linen" program simulates woven fabric substrate (plain weave) with controllable thread finish (dull/shiny) and texture (single strand plastic to multistrand natural fibers).

- **Chen & McCool (2012)** — "Embroidery modeling and rendering" (Graphics Interface 2012). Seminal academic paper on real-time embroidery rendering. Models three fundamental stitch types (long-short, satin, stem/edge) as geometric representations. Renders in texture space with hardware acceleration. The paper demonstrates that stitches rendered in layers (to capture the 2.5D nature of embroidery) at sufficient resolution, with appropriate antialiasing, produce visually convincing results.

- **Cui et al. (2017)** — "Image-based embroidery modeling and rendering" (Computer Animation and Virtual Worlds). Extends the image-based approach using a stitch image database — pre-photographed or pre-rendered stitch segments at various lengths and lighting angles are composited to build the final preview.

- **Adobe Substance 3D Sampler** — Commercial tool with an "Embroidery" generator filter that converts images into embroidery-style textures with PBR material maps (normal, roughness, height). Parameters include density (80-300), thread thickness and length, color count (1-8), smooth areas control, and imperfections. Outputs full material maps for 3D rendering. This is not designed for embroidery production but demonstrates the state of the art in visual embroidery simulation.

**Pros:** Photorealistic results. Can accurately simulate specific fabrics, thread types, and lighting conditions.
**Cons:** Computationally expensive. Requires 3D rendering pipeline. Not necessary for production proofing — mainly for marketing materials and product mockups.

### 16.2 Thread Shading: The Anisotropic Lighting Model

Thread is a fiber — it reflects light differently along its length vs. across it. This **anisotropic reflection** is what gives embroidery its characteristic sheen and directional color variation.

#### The Kajiya-Kay Model (Adapted for Thread)

The Kajiya-Kay model (1989) was developed for hair rendering but applies directly to embroidery thread, since both are thin fibers with cylindrical geometry. The key insight: instead of using a surface normal `N` for lighting calculations, use the **tangent direction** `T` of the fiber.

**The lighting equation:**

```
// Standard diffuse uses dot(N, L)
// Kajiya-Kay replaces this with the fiber tangent:

float sinTL = sqrt(1.0 - dot(T, L) * dot(T, L));
float sinTV = sqrt(1.0 - dot(T, V) * dot(T, V));

// Diffuse component
float diffuse = sinTL;

// Specular component (shifted highlight along fiber)
float specular = pow(max(0, dot(T, L) * dot(T, V) + sinTL * sinTV), shininess);

// Final color
color = threadColor * (ambient + diffuse * lightColor)
      + specularColor * specular * lightColor;
```

Where:
- `T` = tangent direction of the stitch (normalized vector from stitch start to end)
- `L` = direction toward light source
- `V` = direction toward camera/viewer
- `shininess` = specular exponent (higher = tighter highlight). Rayon thread ≈ 40-60, polyester ≈ 20-40, cotton ≈ 5-15

**Why this matters:** The Kajiya-Kay model produces the distinctive **directional sheen** that makes embroidery look realistic. When two adjacent fill rows have different stitch directions (e.g., 45° and -45°), they catch light differently, creating the characteristic "shimmering" effect visible in real satin stitch.

#### Simplified 2D Approximation

For a 2D renderer (Tier 2), you can approximate the anisotropic effect without full 3D math:

1. Define a fixed light direction (e.g., top-left at 45°)
2. For each stitch, compute the angle between the stitch direction and the light direction
3. Map that angle to a brightness modifier: parallel to light = bright highlight, perpendicular = darker
4. Apply as a color shift to the thread color

```python
import math

def compute_stitch_shading(stitch_angle_rad, light_angle_rad=math.radians(45)):
    """
    Compute brightness modifier for a stitch based on its angle
    relative to the light source. Returns 0.7 (shadow) to 1.3 (highlight).
    """
    angle_diff = abs(stitch_angle_rad - light_angle_rad)
    # Normalize to 0..PI/2
    angle_diff = angle_diff % math.pi
    if angle_diff > math.pi / 2:
        angle_diff = math.pi - angle_diff

    # Map: 0 (parallel to light) = highlight, PI/2 (perpendicular) = shadow
    brightness = 1.0 + 0.3 * math.cos(2 * angle_diff)

    return brightness

def shade_thread_color(base_rgb, brightness):
    """Apply brightness modifier to thread color."""
    r, g, b = base_rgb
    return (
        min(255, int(r * brightness)),
        min(255, int(g * brightness)),
        min(255, int(b * brightness))
    )
```

### 16.3 Fabric Substrate Rendering

The fabric background behind embroidery significantly affects the perceived appearance of the design. Different fabrics have different visual properties.

#### Fabric Texture Sources

| Source | Type | Cost | Quality |
|--------|------|------|---------|
| **Photography** | Photograph actual fabric swatches at high DPI | Low (need camera + swatches) | Highest — real fabric |
| **Texture libraries** | Poliigon, 3D Textures, Arroway | $0-50/texture | High — PBR ready |
| **Adobe Substance** | Procedural generators | Subscription | Very high — parametric |
| **Procedural generation** | Generate weave patterns mathematically | Free (development time) | Medium — looks digital |

#### Procedural Fabric Generation

For common embroidery substrates, you can generate fabric textures procedurally:

**Twill weave (common for caps and jackets):**
```python
def generate_twill_texture(width, height, thread_spacing=4, color1=(60, 60, 80), color2=(50, 50, 70)):
    """Generate a simple twill weave pattern."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            # Twill: diagonal pattern
            if (x // thread_spacing + y // thread_spacing) % 3 < 2:
                img[y, x] = color1
            else:
                img[y, x] = color2
    # Add noise for realism
    noise = np.random.normal(0, 3, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return img
```

**Common embroidery fabrics to model:**

| Fabric | Visual Characteristics | Typical Use |
|--------|----------------------|-------------|
| Piqué (polo shirt) | Raised diamond/waffle texture, slight sheen | Polo shirts |
| Twill (cap) | Diagonal rib pattern, matte | Baseball caps, jackets |
| Denim | Visible diagonal weave, indigo/white | Jeans, jackets |
| Canvas/Duck | Heavy plain weave, matte | Bags, workwear |
| Terry cloth (towel) | Looped pile, very textured | Towels |
| Fleece | Smooth, matte, slightly fuzzy | Jackets, blankets |
| Cotton broadcloth | Smooth, slight texture | Dress shirts |

#### Fabric-Stitch Interaction Effects

For realistic simulation, model how stitching interacts with the fabric:

1. **Hoop depression:** The embroidered area sits slightly below the surrounding fabric (from hoop tension). Model as a subtle shadow/gradient at the design boundary.
2. **Stitch height:** Dense embroidery sits above the fabric surface. In 2.5D rendering, draw stitches over the fabric texture with slight drop shadows.
3. **Puckering:** Dense stitching on thin fabric causes visible distortion. This is difficult to simulate procedurally but important for accurate preview of fill-heavy designs on thin fabrics.

---

## 17. Thread Color Catalogue: Data Sources & Architecture {#thread-catalogue}

### 17.1 The Thread Data Landscape

Every embroidery thread manufacturer uses proprietary color numbering systems that don't cross-reference each other. There is no universal standard. Building a digital thread catalogue requires gathering data from multiple manufacturer sources and normalizing it.

### 17.2 Major Manufacturers and Available Data

#### Isacord (by Amann Group)

**Product line:** Isacord 40 (standard weight polyester), 390+ colors
**RGB data availability:** YES — official RGB value documents published by Amann

**Data source:** [RGB Values for Isacord 40 (PDF)](https://www.advancedscreenprintsupply.com/advancedscreenprintsupply/NEW%20SITE-PDFS/AMANN%20BROCHURES/RGB%20Values%20for%20Isacord%2040%20Embroidery%20Thread.pdf) — Contains thread number, color name, and RGB values for all 390 colors.

**Additional sources:**
- [OESD Isacord Thread Chart (PDF)](https://oesd.com/content/assets/Isacord-Thread-Chart.pdf)
- [iMachine Group Isacord RGB Values (PDF)](https://www.imachinegroup.com/pdf/Isacord_RGB.pdf)

**Data format in the PDF:** Tabular — thread number, color name, R, G, B values as integers. Easily parsed into JSON/CSV.

**Confidence:** HIGH — official manufacturer data

#### Madeira

**Product lines:** Classic Rayon 40 (200+ colors), Polyneon polyester (200+ colors), Metallics, Aerofil
**RGB data availability:** YES — via third-party conversion charts and Metro's published data

**Data sources:**
- [Metro Embroidery RGB Chart (PDF)](https://metroemb.com/metroRGB.pdf) — Cross-references Metro color numbers with RGB values AND Madeira catalog numbers
- [Madeira USA Color Cards](https://www.madeirausa.com/color-cards1/) — Official physical and digital shade cards
- [Madeira Pantone Conversion (PDF)](https://d347awuzx0kdse.cloudfront.net/montys/content-file/PMS%20to%20Maderia%20Conversion.pdf) — Maps Madeira numbers to closest Pantone PMS colors
- [EZ Stitch Digitizing Madeira Classic 40 Chart](https://ezstitchdigitizing.com/%F0%9F%A7%B5-madeira-classic-40-thread-color-chart-pdf-download-convert/) — 200+ colors with RGB values, downloadable

**Confidence:** MEDIUM-HIGH — RGB values from third parties, not Madeira directly. Cross-reference multiple sources to validate.

#### Robison-Anton

**Product lines:** Super Brite Polyester (400+ colors), Super Strength Rayon (370+ colors)
**RGB data availability:** LIMITED — some conversion charts include RGB, but no official digital color database found

**Data sources:**
- [Robison-Anton Official Color Charts](http://www.ra-embroidery.com/info/Color-charts_8706l2.aspx)
- [Thread Exchange Conversion Charts](https://www.thethreadexchange.com/miva/merchant.mvc?Screen=CTGY&Category_Code=rastore-conversion-charts) — Cross-brand conversions
- [Robison-Anton Pantone Conversion (Polyester)](https://www.thethreadexchange.com/miva/merchant.mvc?Screen=CTGY&Category_Code=rastore-pantone-to-robison-anton-polyester)
- [Robison-Anton Super Brite Polyester Chart (PDF)](https://www.theunionshop.org/content/threadColorChart.pdf)

**Notable:** Robison-Anton licenses actual Pantone colors for many of their polyester threads, which means the thread physically conforms to Pantone standards. This makes PMS → thread matching more reliable for their brand.

**Confidence:** MEDIUM — RGB values would need to be extracted from physical color card scans or cross-referenced from conversion tools.

#### Sulky

**Product lines:** Rayon 40 (250+ colors), Poly Deco polyester
**RGB data availability:** Available through their online conversion tool

**Data sources:**
- [Sulky Color Conversion Tool](https://sulky.com/color-conversion/) — Online tool converting from DMC, Madeira, Isacord, Robison-Anton to Sulky equivalents
- Physical color cards with thread samples

**Confidence:** MEDIUM

#### Gunold

**Product lines:** Poly 40, Mety (metallics), Sulky licensed lines
**RGB data availability:** YES — published conversion charts with thread data

**Data sources:**
- [Gunold Thread Color Conversion Charts](https://www.gunold.com/thread-color-conversion-charts/) — PDF charts mapping Gunold threads to Pantone PMS numbers and cross-referencing to Madeira, Sulky, Robison-Anton, and Isacord

**Confidence:** MEDIUM-HIGH

### 17.3 Cross-Brand Conversion Tools

These tools are the most practical source for building a unified thread database:

| Tool | URL | Brands Supported | Data Format |
|------|-----|-------------------|-------------|
| **EZ Stitch Thread Converter** | [ezstitchdigitizing.com/free-thread-chart-converter](https://ezstitchdigitizing.com/free-thread-chart-converter/) | All major brands + Pantone | Web tool (scrapeable) |
| **All Threads Converter** | [allthreads.com/ThreadConvert.aspx](https://allthreads.com/ThreadConvert.aspx) | Robison-Anton ↔ all brands | Web tool |
| **ThreadArt Converter** | [threadart.com/pages/thread-conversion-chart](https://www.threadart.com/pages/thread-conversion-chart) | DMC, Madeira, Sulky, Anchor, R-A + hex picker | HTML (scrapeable) |
| **Embroidery Library Calculator** | [emblibrary.com/pages/embroidery-thread-exchange](https://emblibrary.com/pages/embroidery-thread-exchange) | Madeira → 15+ brands | Web tool |
| **Colman & Company Master Chart** | [colmanandcompany.com conversion PDF](https://colmanandcompany.com/blog/wp-content/uploads/2017/11/All-Thread-Conversions-1.pdf) | Royal, Madeira, Isacord, ARC, Rob-Anton | PDF table |
| **OESD Thread Conversion Charts** | [oesd.com/thread-conversion-charts](https://oesd.com/thread-conversion-charts/) | Isacord ↔ Madeira, Sulky, Mettler | PDF |

### 17.4 Building Your Thread Catalogue Database

#### Recommended Data Schema

```json
{
  "thread_id": "ISA-0020",
  "manufacturer": "Isacord",
  "product_line": "Isacord 40",
  "catalog_number": "0020",
  "color_name": "Black",
  "color_rgb": [0, 0, 0],
  "color_hex": "#000000",
  "color_lab": [0, 0, 0],
  "pantone_pms": "Black C",
  "weight": "40wt",
  "material": "polyester",
  "cross_references": {
    "madeira_polyneon": "1800",
    "robison_anton_poly": "5596",
    "sulky_rayon": "1005",
    "gunold_poly": "61005"
  },
  "optical_properties": {
    "sheen": 0.7,
    "thread_diameter_mm": 0.38,
    "fiber_type": "continuous_filament"
  }
}
```

#### Data Collection Strategy

**Phase 1: Isacord (fastest, best documented)**
1. Download the official Amann RGB PDF
2. Parse with a PDF table extractor (e.g., `tabula-py`, `camelot`)
3. Validate RGB values against physical thread cards
4. Output as JSON

**Phase 2: Madeira**
1. Cross-reference Metro RGB chart (has RGB + Madeira numbers)
2. Supplement with EZ Stitch Digitizing chart data
3. Add Pantone mappings from Madeira's official conversion PDF

**Phase 3: Cross-reference**
1. Use Colman & Company master chart PDF to build the cross-reference mapping
2. Validate with EZ Stitch Thread Converter for spot checks
3. Flag discrepancies (no two sources agree perfectly — expect ~5-10% of conversions to differ)

**Phase 4: Extend with optical properties**
1. Assign sheen values by material: rayon ≈ 0.8-0.9 (high sheen), polyester ≈ 0.6-0.7 (medium), cotton ≈ 0.2-0.3 (matte)
2. Assign thread diameters by weight: 40wt ≈ 0.38mm, 30wt ≈ 0.45mm, 60wt ≈ 0.25mm

#### Integration with pyembroidery

pyembroidery's `EmbThread` object already supports the metadata fields you need:

```python
from pyembroidery import EmbThread

# Create thread from your catalogue
thread = EmbThread()
thread.color = 0xFF0000             # RGB as integer
thread.name = "Madeira Classic 1147"
thread.description = "Christmas Red"
thread.brand = "Madeira"
thread.catalog_number = "1147"
thread.chart = "Classic Rayon 40"

# Add to pattern
pattern.add_thread(thread)
```

### 17.5 Color Matching Algorithm

When the user's design uses arbitrary RGB colors, you need to find the closest available thread color from your catalogue. The correct approach is to match in **CIELAB color space** (perceptually uniform) rather than RGB (perceptually non-uniform).

```python
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
# Note: colormath or skimage.color can be used

def rgb_to_lab(r, g, b):
    """Convert RGB (0-255) to CIELAB."""
    srgb = sRGBColor(r / 255.0, g / 255.0, b / 255.0)
    lab = convert_color(srgb, LabColor)
    return (lab.lab_l, lab.lab_a, lab.lab_b)

def find_closest_thread(target_rgb, thread_catalogue):
    """
    Find the closest thread in the catalogue to a target RGB color.
    Uses Delta-E 2000 (CIEDE2000) for perceptually accurate matching.

    Args:
        target_rgb: (r, g, b) tuple, 0-255
        thread_catalogue: List of thread dicts with 'color_rgb' field

    Returns:
        Best matching thread dict and Delta-E distance
    """
    target_lab = rgb_to_lab(*target_rgb)

    best_match = None
    best_delta_e = float('inf')

    for thread in thread_catalogue:
        thread_lab = rgb_to_lab(*thread['color_rgb'])

        # Delta-E 2000 — most perceptually accurate
        target_color = LabColor(*target_lab)
        thread_color = LabColor(*thread_lab)
        de = delta_e_cie2000(target_color, thread_color)

        if de < best_delta_e:
            best_delta_e = de
            best_match = thread

    return best_match, best_delta_e

# Usage
target = (178, 34, 34)  # Firebrick red from design
match, distance = find_closest_thread(target, catalogue)
print(f"Best match: {match['catalog_number']} {match['color_name']} (ΔE={distance:.1f})")
# ΔE < 1: indistinguishable, 1-2: barely noticeable, 2-5: noticeable, >5: obvious difference
```

**Delta-E interpretation for embroidery:**

| Delta-E (CIEDE2000) | Perception | Embroidery Guidance |
|---------------------|------------|---------------------|
| < 1.0 | Imperceptible | Perfect match |
| 1.0 - 2.0 | Barely perceptible | Excellent match — use without concern |
| 2.0 - 3.5 | Noticeable to trained eye | Good match — acceptable for most production |
| 3.5 - 5.0 | Clearly noticeable | Fair — operator should verify visually |
| > 5.0 | Obvious difference | Poor match — flag for user selection |

### 17.6 Fabric Catalogue

Similar to the thread catalogue, build a fabric database for substrate rendering:

```json
{
  "fabric_id": "PIQUE-WHT-001",
  "name": "White Piqué Polo",
  "material": "cotton_poly_blend",
  "weave": "pique_knit",
  "weight_gsm": 220,
  "color_rgb": [250, 248, 245],
  "texture_file": "textures/pique_white_2048.png",
  "normal_map": "textures/pique_white_normal_2048.png",
  "properties": {
    "stretch": 0.15,
    "recommended_stabilizer": "medium_cutaway",
    "pull_compensation_mm": 0.2,
    "max_density_per_cm2": 5000,
    "needle_recommendation": "75/11_ballpoint"
  }
}
```

**Building the fabric catalogue:**
1. Photograph physical fabric swatches under controlled, consistent lighting
2. Create tileable textures (use image editing to make them seamless)
3. Generate normal maps from the photographs (tools: Materialize, NormalMap Online, or Substance Sampler)
4. Record compensation parameters based on production testing

---

## 18. Practical Implementation: Building the Preview Renderer {#renderer-implementation}

### 18.1 Recommended Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Stitch Data  │────▶│ Render Pipeline  │────▶│ Composited Image │
│ (from DST)   │     │                 │     │ (PNG/WebGL)      │
└─────────────┘     │  1. Load fabric  │     └──────────────────┘
                    │  2. Draw stitches │
┌─────────────┐     │  3. Apply shading│
│ Thread       │────▶│  4. Composite   │
│ Catalogue    │     └─────────────────┘
└─────────────┘
```

### 18.2 Option A: Python + Pillow/Cairo (Server-Side Rendering)

Best for: batch processing, server-side preview generation, integration with your existing Python pipeline.

```python
from PIL import Image, ImageDraw
import math
import numpy as np

class EmbroideryRenderer:
    def __init__(self, thread_catalogue, fabric_catalogue):
        self.threads = thread_catalogue
        self.fabrics = fabric_catalogue

    def render(self, pattern, fabric_id, output_size=(2048, 2048), dpi=300):
        """
        Render an embroidery pattern preview.

        Args:
            pattern: pyembroidery EmbPattern object
            fabric_id: ID from fabric catalogue
            output_size: (width, height) in pixels
            dpi: target DPI for physical size mapping
        """
        fabric = self.fabrics[fabric_id]

        # Load or generate fabric texture
        if fabric.get('texture_file'):
            canvas = Image.open(fabric['texture_file']).resize(output_size)
        else:
            canvas = Image.new('RGB', output_size, tuple(fabric['color_rgb']))

        draw = ImageDraw.Draw(canvas)

        # Calculate scale: pattern units (0.1mm) to pixels
        bounds = self._get_bounds(pattern)
        pattern_width = bounds[2] - bounds[0]
        pattern_height = bounds[3] - bounds[1]
        scale = min(
            output_size[0] * 0.85 / max(pattern_width, 1),
            output_size[1] * 0.85 / max(pattern_height, 1)
        )

        offset_x = (output_size[0] - pattern_width * scale) / 2 - bounds[0] * scale
        offset_y = (output_size[1] - pattern_height * scale) / 2 - bounds[1] * scale

        # Thread width in pixels (0.4mm for 40wt)
        thread_px = max(2, int(4 * scale))  # 4 units = 0.4mm

        # Light direction (top-left, 45 degrees)
        light_angle = math.radians(315)

        # Render each stitch
        current_color_idx = 0
        prev_x, prev_y = 0, 0

        for stitch in pattern.stitches:
            x, y, cmd = stitch[0], stitch[1], stitch[2]
            cmd = cmd & 0xFF  # Mask command

            if cmd == 5:  # COLOR_CHANGE
                current_color_idx += 1
                continue
            if cmd in (1, 2, 4):  # JUMP, TRIM, END
                prev_x, prev_y = x, y
                continue
            if cmd != 0:  # Only render STITCH
                prev_x, prev_y = x, y
                continue

            # Screen coordinates
            sx1 = int(prev_x * scale + offset_x)
            sy1 = int(prev_y * scale + offset_y)
            sx2 = int(x * scale + offset_x)
            sy2 = int(y * scale + offset_y)

            # Get thread color
            if current_color_idx < len(pattern.threadlist):
                thread = pattern.threadlist[current_color_idx]
                color = (
                    (thread.color >> 16) & 0xFF,
                    (thread.color >> 8) & 0xFF,
                    thread.color & 0xFF
                )
            else:
                color = (128, 128, 128)

            # Compute stitch angle for shading
            dx = sx2 - sx1
            dy = sy2 - sy1
            if dx == 0 and dy == 0:
                prev_x, prev_y = x, y
                continue

            stitch_angle = math.atan2(dy, dx)
            brightness = self._compute_shading(stitch_angle, light_angle)

            shaded_color = tuple(
                min(255, max(0, int(c * brightness))) for c in color
            )

            # Draw the stitch
            draw.line([(sx1, sy1), (sx2, sy2)],
                      fill=shaded_color, width=thread_px)

            prev_x, prev_y = x, y

        return canvas

    def _compute_shading(self, stitch_angle, light_angle):
        angle_diff = abs(stitch_angle - light_angle)
        angle_diff = angle_diff % math.pi
        if angle_diff > math.pi / 2:
            angle_diff = math.pi - angle_diff
        return 0.8 + 0.4 * math.cos(2 * angle_diff)

    def _get_bounds(self, pattern):
        xs = [s[0] for s in pattern.stitches]
        ys = [s[1] for s in pattern.stitches]
        return (min(xs), min(ys), max(xs), max(ys))
```

### 18.3 Option B: WebGL + Three.js (Client-Side, Interactive)

Best for: web-based preview, interactive zoom/rotate, customer-facing proof approval.

**Architecture:**
- Parse DST file in JavaScript (use a JS port of DST reader, or call Python backend)
- Create Three.js scene with fabric plane as textured mesh
- Render each stitch as a `MeshLine` or instanced tube geometry
- Apply anisotropic shader for thread material
- Enable OrbitControls for interactive viewing

**Key Three.js components:**

```javascript
// Conceptual Three.js embroidery renderer

// 1. Fabric plane
const fabricGeometry = new THREE.PlaneGeometry(200, 200);
const fabricTexture = new THREE.TextureLoader().load('fabric_pique.jpg');
const fabricMaterial = new THREE.MeshStandardMaterial({
    map: fabricTexture,
    normalMap: normalTexture,
    roughness: 0.8
});
const fabric = new THREE.Mesh(fabricGeometry, fabricMaterial);
scene.add(fabric);

// 2. Thread material with anisotropic shading
const threadMaterial = new THREE.ShaderMaterial({
    uniforms: {
        threadColor: { value: new THREE.Color(0xff0000) },
        lightDir: { value: new THREE.Vector3(-1, 1, 1).normalize() },
        shininess: { value: 40.0 }  // Adjust per thread type
    },
    vertexShader: `
        varying vec3 vTangent;
        varying vec3 vWorldPos;
        void main() {
            // Pass tangent direction to fragment shader
            // (derived from stitch direction)
            vWorldPos = (modelMatrix * vec4(position, 1.0)).xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,
    fragmentShader: `
        uniform vec3 threadColor;
        uniform vec3 lightDir;
        uniform float shininess;
        varying vec3 vTangent;
        varying vec3 vWorldPos;

        void main() {
            vec3 T = normalize(vTangent);
            vec3 L = normalize(lightDir);
            vec3 V = normalize(cameraPosition - vWorldPos);

            float sinTL = sqrt(1.0 - pow(dot(T, L), 2.0));
            float sinTV = sqrt(1.0 - pow(dot(T, V), 2.0));

            float diffuse = sinTL;
            float spec = pow(max(0.0,
                dot(T,L)*dot(T,V) + sinTL*sinTV), shininess);

            vec3 color = threadColor * (0.2 + 0.6 * diffuse)
                       + vec3(1.0) * 0.4 * spec;

            gl_FragColor = vec4(color, 1.0);
        }
    `
});

// 3. Create stitch geometry
stitches.forEach(stitch => {
    const geometry = createCapsuleGeometry(
        stitch.x1, stitch.y1,
        stitch.x2, stitch.y2,
        threadDiameter
    );
    const mesh = new THREE.Mesh(geometry, threadMaterial.clone());
    mesh.material.uniforms.threadColor.value.set(stitch.color);
    scene.add(mesh);
});
```

### 18.4 Option C: Canvas 2D API (Lightweight Browser Preview)

Best for: fast, simple browser preview without WebGL dependency.

The HTML5 Canvas 2D API with `lineCap = 'round'` and appropriate `lineWidth` produces acceptable embroidery previews with very little code. Add stitch-angle-based color variation for basic shading.

### 18.5 Renderer Comparison Matrix

| Feature | Python/Pillow | WebGL/Three.js | Canvas 2D |
|---------|--------------|----------------|-----------|
| **Quality** | Medium-High | High | Medium |
| **Speed** | Medium (batch) | Fast (GPU) | Fast |
| **Interactive** | No | Yes (orbit, zoom) | Limited |
| **3D support** | No | Yes | No |
| **Dependencies** | Pillow only | Three.js, WebGL | None (browser) |
| **Use case** | Batch/server | Web app proofing | Quick preview |
| **Anisotropic shading** | Manual per-stitch | GPU shader | Manual per-stitch |
| **Fabric texture** | Image overlay | PBR material | Image underlay |

---

## 19. Visualization: Adjacent Opportunities {#viz-adjacent}

### 19.1 Stitch Simulation / Animation (High Relevance)

Animate the stitching process — show stitches appearing in sequence, simulating how the machine will actually sew the design. This is extremely valuable for production planning (spotting sequencing issues) and customer engagement (watching the design "come to life").

Ink/Stitch includes a basic stitch simulator that animates stitch placement. This could be extended with your renderer to produce animated GIFs or video previews.

**Signal strength:** HIGH — Differentiator for your tool. Few tools do this well.

**Next step:** Implement frame-by-frame rendering where each frame adds N stitches to the preview.

### 19.2 AR/On-Garment Preview (Medium Relevance)

Use augmented reality to preview embroidery placement on actual garments. The user photographs a garment, places the embroidery design on it, and sees a composite preview. This requires image recognition for garment detection and perspective-correct overlay of the embroidery render.

**Signal strength:** MEDIUM — High customer value, but significant additional development.

**Next step:** Research ARKit/ARCore for mobile, or OpenCV perspective transforms for web.

### 19.3 Thread Inventory Management (High Relevance)

Track which threads you physically have in stock, alert when a design requires a color you don't own, suggest substitutions from in-stock inventory using the Delta-E matching algorithm. This directly supports your stated goal of making sure you have the correct colors.

**Signal strength:** HIGH — Directly addresses production workflow need.

**Next step:** Build an inventory layer on top of the thread catalogue, with quantities and re-order triggers.

---

## 20. Visualization: Competing Perspectives & Counterarguments {#viz-counterarguments}

### "Realistic preview doesn't match reality anyway"

The strongest counterargument against investing heavily in visualization: even the best digital preview cannot perfectly predict how embroidery will look on a specific fabric because thread sheen varies by viewing angle, fabric texture interacts unpredictably with stitch patterns, tension settings and stabilizer choices affect the final appearance, and monitors vary widely in color reproduction. Every thread manufacturer explicitly warns that digital color charts are approximate.

**Why this doesn't invalidate the effort:** The goal isn't photographic accuracy — it's **directional accuracy**. A preview that's 85% accurate lets the operator catch problems (wrong color, bad stitch direction, missing coverage) before they waste machine time and materials. The alternative — no preview, just trust the file — is far worse.

### "Just use a commercial previewer"

Tools like Wilcom's TrueSizer (free viewer) or Hatch Embroidery's preview already do this well. Why build your own?

**Counter:** If your tool generates the embroidery files, having the preview integrated means the user sees the result immediately, without switching software. The preview also becomes a feedback loop for adjusting generation parameters. And commercial previewers can't be embedded in your custom workflow or web application.

---

## 21. Visualization: Horizon Pointers {#viz-horizon}

**Neural style transfer for embroidery:** Research has demonstrated using deep learning to transfer the visual style of specific embroidery traditions (Cantonese embroidery, Japanese sashiko) onto arbitrary images. This could allow generating designs that look authentically "hand-embroidered" in a specific cultural style.

**Real-time video overlay:** Projecting the embroidery preview directly onto fabric using a projector mounted above the machine. Used in some high-end production environments for placement verification.

**Thread color spectrophotometry:** Rather than relying on RGB approximations, some enterprises use spectrophotometers (X-Rite, Datacolor) to measure actual thread colors and build highly accurate digital catalogs. The resulting spectral data provides far more accurate color matching than RGB alone.

**Digital twin of the embroidery machine:** Model the specific mechanical behavior of your Barudan machines (tension, speed, bobbin interaction) to predict and visualize stitch formation more accurately.

**GAN-based texture synthesis:** Using generative adversarial networks to create photorealistic embroidery textures from stitch data, trained on photographs of actual embroidered samples. This is the emerging frontier for replacing the manual tuning of rendering parameters.

---

## 22. Visualization: Sources & Confidence {#viz-sources}

### Sources Used

**Rendering Algorithms:**
- [Chen, McCool et al. — "Embroidery modeling and rendering" (Graphics Interface 2012)](https://graphicsinterface.org/proceedings/gi2012/gi2012-17/) — Seminal paper on real-time embroidery rendering. Confidence: HIGH
- [Chen, McCool, Kitamoto — "Embroidery modeling and rendering in real time" (SIGGRAPH)](https://history.siggraph.org/learning/embroidery-modeling-and-rendering-in-real-time-by-chen-mccool-and-kitamoto/) — Real-time rendering approach. Confidence: HIGH
- [Cui et al. — "Image-based embroidery modeling and rendering" (2017)](https://onlinelibrary.wiley.com/doi/10.1002/cav.1725) — Image-based stitch rendering. Confidence: HIGH
- [Zhenyuan et al. — "Directionality-Aware Design of Embroidery Patterns" (2023, Computer Graphics Forum)](https://onlinelibrary.wiley.com/doi/10.1111/cgf.14770) — Vector field-based stitch direction. Confidence: HIGH
- [US Patent US20120101790A1 — "Embroidery image rendering using parametric texture mapping"](https://patents.google.com/patent/US20120101790A1/en) — Commercial rendering approach. Confidence: HIGH
- [POV-Ray Thread Project](https://dnyarri.github.io/povthread.html) — Open-source 3D thread/stitch simulation. Confidence: HIGH
- [ResearchGate — "Thread-based BRDF rendering on GPU"](https://www.researchgate.net/publication/251987762_Thread-based_BRDF_rendering_on_GPU) — GPU-based fiber shading. Confidence: HIGH
- [Ink/Stitch Realistic Rendering Issue #40](https://github.com/inkstitch/inkstitch/issues/40) — Community discussion on Ink/Stitch rendering. Confidence: MEDIUM

**Thread Color Data:**
- [Amann/Isacord RGB Values PDF](https://www.advancedscreenprintsupply.com/advancedscreenprintsupply/NEW%20SITE-PDFS/AMANN%20BROCHURES/RGB%20Values%20for%20Isacord%2040%20Embroidery%20Thread.pdf) — Official manufacturer RGB data. Confidence: HIGH
- [Metro Embroidery RGB Chart](https://metroemb.com/metroRGB.pdf) — Cross-reference with Madeira. Confidence: MEDIUM-HIGH
- [Madeira USA Color Cards](https://www.madeirausa.com/color-cards1/) — Official Madeira resources. Confidence: HIGH
- [Madeira Pantone Conversion PDF](https://d347awuzx0kdse.cloudfront.net/montys/content-file/PMS%20to%20Maderia%20Conversion.pdf) — Madeira ↔ Pantone mapping. Confidence: HIGH
- [Robison-Anton Official Color Charts](http://www.ra-embroidery.com/info/Color-charts_8706l2.aspx) — Confidence: HIGH
- [Robison-Anton Pantone Conversion](https://www.thethreadexchange.com/miva/merchant.mvc?Screen=CTGY&Category_Code=rastore-pantone-to-robison-anton-polyester) — Confidence: MEDIUM-HIGH
- [OESD Isacord Thread Chart](https://oesd.com/content/assets/Isacord-Thread-Chart.pdf) — Confidence: HIGH
- [OESD Thread Conversion Charts](https://oesd.com/thread-conversion-charts/) — Confidence: HIGH
- [Gunold Conversion Charts](https://www.gunold.com/thread-color-conversion-charts/) — Confidence: MEDIUM-HIGH
- [EZ Stitch Thread Converter](https://ezstitchdigitizing.com/free-thread-chart-converter/) — Confidence: MEDIUM
- [ThreadArt Conversion Chart](https://www.threadart.com/pages/thread-conversion-chart) — Confidence: MEDIUM
- [Sulky Color Conversion Tool](https://sulky.com/color-conversion/) — Confidence: MEDIUM
- [Colman & Company Master Conversion Chart](https://colmanandcompany.com/blog/wp-content/uploads/2017/11/All-Thread-Conversions-1.pdf) — Confidence: MEDIUM-HIGH

**Fabric & Material Rendering:**
- [Adobe Substance 3D Sampler — Embroidery Generator](https://helpx.adobe.com/substance-3d-sampler/filters/generators/embroidery.html) — Commercial reference. Confidence: HIGH
- [Khattar et al. — "Texture-Free Practical Model for Woven Fabrics" (2025, Computer Graphics Forum)](https://onlinelibrary.wiley.com/doi/10.1111/cgf.15283) — Academic fabric rendering. Confidence: HIGH

**Visualization Tools:**
- [pyembroidery PNG/SVG output](https://github.com/EmbroidePy/pyembroidery) — Confidence: HIGH
- [Ink/Stitch Visualization](https://inkstitch.org/docs/visualize/) — Confidence: HIGH
- [PEmbroider visualize()](https://github.com/CreativeInquiry/PEmbroider) — Confidence: HIGH
- [Embird Thread Catalog System](https://www.embird.net/studio/manual/0380colors.htm) — Confidence: MEDIUM

### Significant Information Gaps (Visualization-Specific)

1. **No manufacturer thread color API:** No thread manufacturer offers a programmatic API for color data. All data must be extracted from PDFs, web tools, or physical color cards. This means your thread catalogue requires manual data collection and periodic updates when manufacturers add/discontinue colors.

2. **Limited RGB accuracy:** All RGB values for threads are approximations. Thread is a 3D physical object with anisotropic reflectance — it cannot be perfectly represented by a single RGB value. The same thread looks different under daylight vs. fluorescent light, and changes appearance based on stitch direction and density.

3. **No open-source production-quality stitch renderer:** While Ink/Stitch, pyembroidery, and PEmbroider all produce visual output, none achieves the rendering quality of commercial tools like Wilcom or Hatch. The gap is primarily in the anisotropic shading — no open-source project implements the Kajiya-Kay model for embroidery thread specifically.

4. **Fabric-specific compensation data:** How thread appearance changes on different fabrics (absorption, contrast, pile interaction) is not documented in any systematic way. This is knowledge held by experienced digitizers.

### Overall Confidence (Visualization Section): **MEDIUM-HIGH**

The rendering algorithms are well-established in academic literature and have commercial implementations proving feasibility. Thread color data is available but requires collection effort. The main uncertainty is in achieving commercial-grade visual quality with open-source tools — feasible but requires significant shader development.
