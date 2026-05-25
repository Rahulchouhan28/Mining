# Mining Plan Generator

Year-wise mining plan generator for Indian statutory plans (MCDR / DGM Rajasthan style). Upload existing plans / maps / Excel data, and the app auto-extracts the lease boundary, runs an inward-buffer pit slicer in UTM 43 N, and produces statutory-style A3 PDF plates, KML / KMZ / GeoJSON, an Excel quantity table, an alternative-comparison plate, and a multi-page engineering report.

> **Conceptual output only.** Every generated PDF carries the verbatim certification clause. Final statutory submission must be reviewed and signed by a qualified mining engineer / RQP / competent person.

## Architecture

```
d:\year wise plans\
├── apps/
│   ├── web/    ← Next.js 16 (App Router) + TS + Tailwind v4 — runs on :3000
│   └── api/    ← FastAPI + Python 3.12 — runs on :8000
├── shared/schemas/    ← JSON schema (single source of truth for the data model)
├── sample/haripura/   ← Sample project payload
├── projects/          ← Per-project storage (runtime, .gitignored)
└── docs/              ← (reserved for future docs)
```

The web app proxies `/api/*` → FastAPI via `next.config.ts` rewrites, so the browser only ever talks to `http://localhost:3000`.

State persistence in v1 is on-disk JSON: one folder per project under `projects/<slug>/` containing `project.json`, `uploads/`, and `exports/`. No database, no auth.

## Prerequisites

- Node ≥ 22 (tested with 24.15)
- Python ≥ 3.12
- npm ≥ 10

## First-time setup

```powershell
# from the repo root
npm install                                       # installs concurrently
cd apps\web; npm install; cd ..\..
python -m venv apps\api\.venv
apps\api\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt
```

## Run locally

```powershell
npm run dev
```

This starts both servers concurrently:

- Web: <http://localhost:3000>
- API: <http://localhost:8000> (docs at <http://localhost:8000/docs>)

## Run tests

```powershell
npm run test:api
```

Tests cover the projection round-trip (the 7.5 m statutory barrier in UTM 43 N), the year-wise quantity formulas, and the A3 PDF composer.

## Happy-path flow (3 screens)

The sidebar groups screens into **Happy path** (1, 2, 6, 9) and **Advanced** (3, 4, 5, 7, 8). The advanced screens are reachable from the sidebar but the auto-prepare flow skips them.

1. **Project Setup** (`/project/new`) — basic project details. "Load Sample" pre-fills the Haripura values.
2. **Upload Plans** — 11 upload cards (Surface, Geological, Section, Environment, Key, PMCP, Conceptual, FAP, Borehole, Chemical Analysis, Production). Accept PDF / KML / KMZ / GeoJSON / image / Excel / CSV. Click **Generate Year-Wise Plan** at the bottom-right and the backend:
   - parses the largest polygon from any uploaded KML / KMZ / GeoJSON as the lease, *or* synthesizes a square lease from the area you entered on step 1 if you only uploaded PDFs / images;
   - seeds engineering inputs with conceptual defaults (flagged `ASSUMED — NEEDS VALIDATION`);
   - runs the year-wise pit slicer in UTM 43 N for `base`, `conservative`, `aggressive`.
3. **Year-Wise Plan** — the generated plan with:
   - **Approach tabs** at the top — switch between base / conservative / aggressive instantly (no recompute);
   - Map and per-year quantity table for the active approach;
   - A collapsible **Adjust parameters &amp; re-generate** block under the table for tweaking production target, bench height, density, recovery, plan years;
   - A floating **Convert {approach} to PDF** button at the bottom-right.
4. **Export Center** — direct downloads for everything: per-approach PDF plates, alternative-comparison plate (A3 side-by-side), engineering report (A4, multi-page narrative), GeoJSON, KML, Excel quantity table, and a single ZIP package matching the spec Section 9 layout.

## Advanced screens (still reachable from sidebar)

- **Step 3 — Digitize Map Layers**: Leaflet + Geoman editor with full draw / edit tools, optional 2-corner georeferenced raster underlay from any uploaded PDF / image, and auto-generation of the 7.5 m statutory barrier on lease draw.
- **Step 4 — Engineering Inputs**: full form for all six input sections (Production / Bench / Mineral & Waste / Machinery / Grade / Environmental Constraints). Tags every default-filled field with the ASSUMED chip.
- **Step 5 — Alternatives**: explicit alternative picker (Base / Conservative / Aggressive are live; D–H are visible but disabled, marked "Coming in v2").
- **Step 7 — Review &amp; Edit**: layer toggles per year, approval checkbox, edit existing polygons.
- **Step 8 — PDF Composer**: paper / orientation / scale / plate-type selection for one-off PDF generation.

## Smoke test (load the sample project)

```powershell
# with the API running
$sample = Get-Content -Raw sample\haripura\project.json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/projects -ContentType "application/json" -Body $sample
```

Then visit <http://localhost:3000> — the Haripura project will appear on the landing page.

## What's done vs deferred

**Phase 1 (MWP) — done:** project CRUD, all 11 upload cards, auto-extract lease from KML/KMZ/GeoJSON, synthetic-square fallback, year-wise pit slicer in UTM 43 N, quantity formulas, validation, Cartopy + Matplotlib A3 plate, alternative-comparison plate, multi-page engineering report (ReportLab), GeoJSON / KML / Excel exports, ZIP package matching spec §9.

**Phase 2 — still deferred:** OpenCV-based auto-detection of layers from scanned PDFs (research-grade, 20–70 % accuracy), the five additional alternatives (D–H), borehole-CSV→map-point ingest, Postgres / multi-user / auth.
