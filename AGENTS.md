# Repo-specific guidance for Codex

## What this app is
Year-wise mining plan generator for Indian statutory plans (MCDR, DGM Rajasthan minor-mineral rules). Read [MINING_PLAN_GENERATOR_INTERFACE_FLOW.md](MINING_PLAN_GENERATOR_INTERFACE_FLOW.md) for the original spec and [README.md](README.md) for the implemented happy-path flow. The implementation plan from session 1 lives at `~/.Codex/plans/hey-Codex-read-mining-plan-generator-in-piped-aho.md`.

## Architecture facts to memorize
- **Split stack.** Next.js 16 (App Router) on :3000, FastAPI on :8000. Browser only ever sees :3000 — `/api/*` is proxied to FastAPI via `next.config.ts` rewrites.
- **No DB.** Each project is `projects/<slug>/{project.json, uploads/, exports/}` on disk. CRUD goes through `apps/api/storage.py`.
- **Single source of truth** for the data model: `shared/schemas/project.schema.json`. If you change a field, change it here first.
- **Happy path is 4 screens (1 → 2 → 6 → 9).** The other 5 are "Advanced" — reachable from the sidebar but the `POST /api/projects/<slug>/auto-prepare` flow skips them by parsing the lease from uploads, seeding engineering defaults, and running the planner in one call.

## Critical GIS conventions
- **All buffering, area, distance — projected meters in EPSG:32643 (UTM 43 N), never WGS 84.** The 7.5 m statutory barrier in particular is silently wrong if computed in degrees. Use `services/projection.py` (`geom_to_utm` / `geom_to_wgs`).
- **Storage CRS is WGS 84 (EPSG:4326)** because that's what GeoJSON, Leaflet, and KML expect. Reproject at the boundary, not throughout.
- For Rajasthan west of 72° E (Barmer, Jaisalmer west), the zone is **EPSG:32642** — not yet handled. Add when needed.

## Auto-extract flow
`services/extract.py::auto_prepare(slug)` is the entry point invoked by the upload screen's "Generate Year-Wise Plan" button. It walks `uploaded_files` looking for `.kml`, `.kmz`, `.geojson` (in that priority) and parses the largest polygon as the lease. If no vector file is found, it synthesizes a square in UTM 43 N sized from `project_details.area_ha`, centered at the Haripura default (27.20°N 73.65°E). It also fills in `engineering_inputs` with conceptual defaults and tags every seeded field path in `engineering_inputs.assumed_fields`. The PUT-back is followed by `services/year_planner.generate_for_project` for all three default alternatives. **Never** silently overwrite a user's existing lease — only replace when re-running auto-prepare, and always preserve other digitized features.

## Next.js 16 gotchas (this is NOT Next 15)
The scaffold's `apps/web/AGENTS.md` warns: read `node_modules/next/dist/docs/01-app/` before writing components. Notable changes from training-data Next 15:
- Turbopack is the default dev bundler — set `turbopack.root` in `next.config.ts` when the repo root has a separate `package.json`.
- React 19.2 — Server Components are default; `params` in layouts/pages is a `Promise<{...}>` and must be `await`ed.
- Tailwind v4 (PostCSS plugin `@tailwindcss/postcss`, no `tailwind.config.js` by default).
- For Leaflet (DOM-only): import via `next/dynamic` with `ssr: false`. See `components/digitize/DigitizeScreen.tsx` for the pattern.

## Python conventions
- Run tests with the root script: `npm run test:api`. Direct invocation needs `PYTHONPATH=apps/api`.
- Service modules go in `apps/api/services/`, routes in `apps/api/routes/`.
- Don't import from `apps/web/` — backend never knows about the frontend.
- Matplotlib backend must be set to `Agg` *before* any pyplot import in any service module that renders PDFs (`pdf_composer.py`, `comparison_pdf.py`). Otherwise the server tries to open a display.

## Theme (Section 12 of the spec)
- Primary: deep navy / slate-900
- Accent: mining orange / amber-500, safety yellow
- Cards: white with soft shadow, slate-200 border
- Map background: slate-50

## The certification clause
Every generated PDF and report must carry this text verbatim (from spec Section 8):

> THIS PLAN IS GENERATED FROM USER-UPLOADED MAPS AND ENGINEERING INPUTS. FINAL STATUTORY SUBMISSION MUST BE VERIFIED AND SIGNED BY A QUALIFIED MINING ENGINEER / RQP / COMPETENT PERSON.

Do not paraphrase. Do not omit. This is what keeps the app on the right side of statutory law. The string lives once in each PDF service (`pdf_composer.py`, `comparison_pdf.py`, `report_pdf.py`) — when editing, edit all three.

## Don't auto-detect (yet)
The "Auto Detect Layers" button on the digitize screen is intentionally stubbed. OpenCV-based vectorization of scanned plates is research-grade — 20-70 % accuracy with cleanup time often exceeding redraw time. v1 ships with manual digitization over a georeferenced raster underlay only, and the auto-prepare flow uses vector uploads or a synthetic-square fallback — never PDF/image vectorization.
