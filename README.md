# Embroidery Processing

Custom embroidery file generation and management system for Straight Down's Barudan machine operation.

## Overview

This project validates the technical feasibility of building an end-to-end embroidery production platform — from image input to machine-ready DST files. The system is designed to integrate with NetSuite for order management, provide customer-facing proof approval, support design adjustment, and manage production dispatch to Barudan machines via BNet software.

## POC Roadmap

The project is structured as 8 sequential proof-of-concept phases, ordered by risk:

1. **DST Smoke Test** — Generate valid DST files that Barudan machines accept
2. **Stitch Generation** — Convert vector paths into production-quality stitch patterns
3. **Image to Regions** — Segment input images into stitchable color regions
4. **Stitch Preview Renderer** — Visual preview of stitch output before production
5. **Thread Catalogue** — Madeira thread color matching and management
6. **Interactive Region Editor** — UI for adjusting stitch regions and parameters
7. **End-to-End Integration** — Full pipeline from image to DST
8. **Order Workflow** — NetSuite integration and production dispatch

## Tech Stack

- **Language:** Python 3.10+
- **Frontend:** HTML/CSS/JS (where visualization is needed)
- **Target machine:** Barudan embroidery machines via BNet
- **Output format:** DST (Tajima)
- **Thread brand:** Madeira (Classic Rayon 40, Polyneon)
- **Input types:** SVG vector files, PNG/JPG raster logos

## Getting Started

_Setup instructions will be added as POC development begins._

## License

Proprietary — Straight Down Clothing Co.
