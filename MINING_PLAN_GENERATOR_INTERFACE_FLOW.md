# Mining Plan Generator — Interface Flow & Claude Code Prompt

## Goal

Create a clean web interface where the user can:

1. Enter basic project details.
2. Upload mining plan files such as PDF, KML, KMZ, GeoJSON, DWG-exported PDF, or image maps.
3. Select the type of plan to generate.
4. Select planning alternatives.
5. Generate a year-wise mining plan.
6. Preview the generated plan in the same style as statutory mining plan PDFs.
7. Check/edit the plan.
8. Convert/export the final plan to downloadable PDF, KML/KMZ, GeoJSON, Excel and ZIP.

The final generated plan should visually look like professional mining plan sheets with:
- Lease boundary
- 7.5 m statutory barrier
- Grid lines
- North arrow
- Scale bar
- Legend/index
- Year-wise pit limits
- Year-wise overburden
- Year-wise topsoil stack
- Year-wise plantation
- Backfill area
- Haul road
- Drainage/garland drain
- Settling tank
- Title block
- Certification box
- Downloadable PDF output

---

# 1. User Interface Flow

## Screen 1 — Welcome / Project Setup

### Purpose
Ask the user for basic project details before uploading any maps.

### UI Layout
Create a modern dashboard-style page with a centered form card.

### Form Title
**Create New Mining Plan Project**

### Form Fields

```json
{
  "project_name": "Haripura Limestone Block TKSB-18",
  "applicant_name": "M/s. Example",
  "mineral": "Limestone",
  "village": "Haripura",
  "tehsil": "Kheenvsar",
  "district": "Nagaur",
  "state": "Rajasthan",
  "area_ha": 4.8,
  "map_type": "surface_plan",
  "scale": "1:1000"
}
```

### Required Input Fields

| Field | Type | Example |
|---|---|---|
| Project Name | Text | Haripura Limestone Block TKSB-18 |
| Applicant Name | Text | M/s. Suncity Chemical & Minerals Pvt. Ltd. |
| Mineral | Dropdown/Text | Limestone |
| Village | Text | Haripura |
| Tehsil | Text | Kheenvsar |
| District | Text | Nagaur |
| State | Dropdown/Text | Rajasthan |
| Area in Hectare | Number | 4.8 |
| Main Map Type | Dropdown | Surface Plan |
| Scale | Dropdown/Text | 1:1000 |
| Survey Date | Date | 10-03-2025 |
| Plan Period | Dropdown | 1 year / 2 year / 3 year / 4 year / 5 year |

### Map Type Dropdown Options

```text
Surface Plan
Surface Geological Plan
Geological Plan
Geological Section
Progressive Mine Closure Plan
Conceptual Plan
Environment Plan
Key Plan
Financial Assurance Plan
Year-Wise Mining Plan
Other
```

### Buttons

```text
Save & Continue
Load Sample Project
Reset
```

---

# 2. Screen 2 — Upload Plans / Maps

## Purpose
User uploads existing plans in PDF, KML, KMZ, GeoJSON or image format.

## Page Title
**Upload Mining Plans & GIS Files**

## Upload Sections

### A. Main Plan Upload

Allow user to upload:

```text
PDF
KML
KMZ
GeoJSON
JPG
PNG
TIFF
DWG exported as PDF
Excel
CSV
```

### B. Upload Cards

Create separate upload cards:

| Upload Card | Accepted Files |
|---|---|
| Surface Plan | PDF, KML, KMZ, GeoJSON, Image |
| Geological Plan | PDF, KML, KMZ, GeoJSON, Image |
| Geological Section | PDF, Image |
| Environment Plan | PDF, Image |
| Key Plan | PDF, Image |
| Progressive Mine Closure Plan | PDF, Image |
| Conceptual Plan | PDF, Image |
| Financial Assurance Plan | PDF, Excel, Image |
| Borehole Data | Excel, CSV, PDF |
| Chemical Analysis | Excel, CSV, PDF |
| Production Data | Excel, CSV, PDF |

### C. File Preview

After upload, show:

```text
File name
File type
File size
Detected map type
Number of pages if PDF
Preview button
Remove button
```

### D. PDF Preview

If PDF is uploaded:
- Show page thumbnails.
- Allow user to choose the page to digitize.
- Allow zoom and pan.
- Allow rotation.
- Allow crop to map area.

### E. KML/KMZ Preview

If KML/KMZ is uploaded:
- Parse layers.
- Show boundary and polygon overlays on map.
- Allow user to assign layer type.

### Buttons

```text
Back
Continue to Layer Extraction
```

---

# 3. Screen 3 — Layer Extraction / Digitization

## Purpose
The system should either auto-detect or allow manual marking of mining layers.

## Page Title
**Extract / Digitize Map Layers**

## Map Canvas
Use Leaflet, MapLibre, or OpenLayers.

## Required Layer Types

```text
Lease Boundary
7.5 m Statutory Barrier
60 m Boundary
500 m Boundary
Grid Lines
Contour
Road / Rasta
Existing Tank
Existing Infrastructure
Existing Electric Line
Existing Borehole
Proposed Borehole
Geological Zone
Ultimate Pit Limit
Year I Pit
Year II Pit
Year III Pit
Year IV Pit
Year V Pit
Overburden Dump
Topsoil Stack Yard
Backfill Area
Plantation Area
Mineral Stack Yard
Haul Road
Garland Drain
Settling Tank
Retaining Wall
Fencing
Office / Labour Shed
Water Reservoir
Village / Habitation
Temple / Sensitive Structure
```

## Tools

```text
Draw Polygon
Draw Line
Draw Point
Edit Shape
Delete Shape
Move Label
Assign Layer Type
Assign Year
Assign Alternative
Calculate Area
Set Color
Lock Layer
Unlock Layer
```

## Auto-Detection Option

Add a button:

```text
Auto Detect Layers
```

When clicked, system should attempt to identify colored lines, boundaries and text labels from PDF/image.

If auto-detection is not accurate, user can manually trace.

## Manual Georeferencing

Allow user to set coordinates using:

```text
Known point 1 coordinate
Known point 2 coordinate
Scale bar length
Map scale
Coordinate system
```

## Buttons

```text
Save Layers
Continue to Engineering Inputs
```

---

# 4. Screen 4 — Engineering Inputs

## Purpose
Ask technical mining parameters required for quantity calculation and plan generation.

## Page Title
**Engineering Inputs**

## Sections

### A. Production Details

```json
{
  "annual_production_target_tonnes": 50000,
  "approved_capacity_tonnes_per_year": 50000,
  "working_days_per_year": 250,
  "shifts_per_day": 1,
  "hours_per_shift": 8
}
```

### B. Bench Design

```json
{
  "bench_height_m": 6,
  "bench_width_m": 6,
  "face_slope_degree": 70,
  "overall_pit_slope_degree": 45,
  "ultimate_pit_depth_m": 42
}
```

### C. Mineral and Waste Data

```json
{
  "bulk_density_t_per_m3": 2.4,
  "topsoil_thickness_m": 0.3,
  "overburden_thickness_m": 1.0,
  "mineral_recovery_percent": 90,
  "reject_percent": 10
}
```

### D. Machinery

```json
{
  "excavator_bucket_capacity_m3": 1.2,
  "number_of_excavators": 1,
  "dumper_capacity_tonnes": 16,
  "number_of_dumpers": 3,
  "crusher_capacity_tph": 100,
  "drill_machine_available": true,
  "blasting_required": true
}
```

### E. Grade / Chemical Analysis

For limestone, allow:

```text
CaCO3 %
CaO %
MgO %
SiO2 %
Al2O3 %
Fe2O3 %
LOI %
Moisture %
```

For other minerals, allow custom grade fields.

### F. Environmental Constraints

```text
Water body distance
Village distance
Temple/sensitive structure distance
Electric line present
Nala/drainage present
Forest land present
Private land present
Government land present
```

## Default Values

If user does not know values, show:

```text
Use Conceptual Default Values
```

But mark all such values as:

```text
ASSUMED — NEEDS VALIDATION
```

## Buttons

```text
Back
Save Inputs
Continue to Alternative Selection
```

---

# 5. Screen 5 — Alternative Selection

## Purpose
User chooses the type of mining plan alternatives to generate.

## Page Title
**Choose Planning Alternatives**

## Alternative Cards

### Alternative A — Conservative Plan
Lower production, minimum disturbance, slow pit advancement.

### Alternative B — Base Plan
Balanced plan following uploaded mining layout and standard five-year development.

### Alternative C — Aggressive Plan
Maximum permitted production, faster excavation and larger machinery requirement.

### Alternative D — Low-Waste / Backfill Priority Plan
Minimizes external overburden dump and prioritizes backfilling.

### Alternative E — Environment-Sensitive Plan
Avoids tanks, habitation, roads, temples, electric lines and sensitive areas.

### Alternative F — Cost-Optimized Plan
Minimizes haul distance, road length, machinery movement and cost.

### Alternative G — Grade-Blending Plan
Plans excavation based on grade zones and buyer specification.

### Alternative H — Minimum-Disturbance Plan
Minimizes disturbed area and delays private/sensitive land disturbance.

## UI Feature
Allow checkboxes:

```text
[ ] Conservative
[ ] Base
[ ] Aggressive
[ ] Low-Waste
[ ] Environment-Sensitive
[ ] Cost-Optimized
[ ] Grade-Blending
[ ] Minimum-Disturbance
```

Default selected:

```text
Base
Conservative
Aggressive
```

## Buttons

```text
Back
Generate Plan
```

---

# 6. Screen 6 — Generate Year-Wise Plan

## Purpose
System generates year-wise map layers and quantity tables.

## Page Title
**Generate Year-Wise Mining Plan**

## Generated Layers

For each selected alternative, generate:

```text
Year I Pit Limit
Year II Pit Limit
Year III Pit Limit
Year IV Pit Limit
Year V Pit Limit
Year-wise OB Dump
Year-wise Topsoil Stack
Year-wise Backfill
Year-wise Plantation
Haul Road
Garland Drain
Settling Tank
Retaining Wall
Mineral Stack Yard
Office/Labour Shed
Fencing
```

## Calculations

Calculate:

```text
Pit Area
Excavation Volume
Mineral Volume
Mineral Tonnage
Saleable Mineral
Topsoil Quantity
Overburden Quantity
Backfill Volume
Plantation Area
Stripping Ratio
Equipment Requirement
Daily Production Target
Monthly Production Target
```

## Quantity Formula

```text
Excavation Volume = Pit Area × Average Depth
Mineral Tonnage = Mineral Volume × Bulk Density
Saleable Mineral = ROM × Recovery %
Topsoil Quantity = Disturbed Area × Topsoil Thickness
OB Quantity = OB Area × OB Thickness
Stripping Ratio = Waste / Mineral
```

## Validation Rules

Show warnings if:

```text
Pit crosses lease boundary
Pit enters 7.5 m statutory barrier
Dump overlaps active pit
Dump is too close to tank/nala
Road is disconnected
Production exceeds approved capacity
Bench depth does not match bench height
Missing density/topsoil/OB values
Missing chemical analysis
```

## Buttons

```text
Regenerate
Edit Manually
Save Generated Plan
Continue to Review
```

---

# 7. Screen 7 — Review and Edit Generated Plan

## Purpose
User checks the generated plan visually before export.

## Page Title
**Review Generated Mining Plan**

## Interface

Left side:
- Layer panel
- Alternative selector
- Year selector
- Toggle visibility

Center:
- Generated mining plan map

Right side:
- Quantity summary
- Validation warnings
- Edit tools

## View Controls

```text
Show All Years
Show Year I
Show Year II
Show Year III
Show Year IV
Show Year V
Show Pit Only
Show OB Only
Show Topsoil Only
Show Plantation Only
Show Backfill Only
Show Final Plan
```

## Editing Tools

```text
Move Polygon
Resize Polygon
Edit Vertex
Delete Layer
Add Label
Change Color
Recalculate Quantity
Undo
Redo
```

## Approval Checkbox

Before export, user must tick:

```text
[ ] I have reviewed the generated plan and understand that final statutory submission must be verified by a qualified mining engineer.
```

## Buttons

```text
Back
Save Edits
Preview PDF
Convert to PDF
```

---

# 8. Screen 8 — PDF Map Composer

## Purpose
Compose the final statutory-style PDF sheet.

## Page Title
**PDF Map Composer**

## Sheet Options

```text
Paper Size: A4 / A3 / A2 / A1
Orientation: Landscape / Portrait
Scale: 1:1000 / 1:2000 / 1:5000 / Custom
Map Type: Year-Wise Mining Plan / Progressive Mine Closure Plan / Conceptual Plan / Environment Plan
```

## Must Include

```text
North Arrow
Scale Bar
Coordinate Grid
Legend / Index
Title Block
Certification Box
Prepared By
Date
Plate Number
Mine Details
Applicant Details
Mineral
Area
Scale
Survey Date
```

## Title Block Example

```text
YEAR-WISE MINING PLAN OF HARIPURA LIMESTONE BLOCK TKSB-18
N/v - Haripura, Tehsil - Kheenvsar, Distt. - Nagaur (Raj.)
Mineral - Limestone
Applicant - M/s. Example
Area - 4.800 Hect.
Scale - 1:1000
```

## Certification Box

```text
THIS PLAN IS GENERATED FROM USER-UPLOADED MAPS AND ENGINEERING INPUTS.
FINAL STATUTORY SUBMISSION MUST BE VERIFIED AND SIGNED BY A QUALIFIED MINING ENGINEER / RQP / COMPETENT PERSON.
```

## Preview
Show final sheet preview before download.

## Buttons

```text
Back to Edit
Generate PDF
Download PDF
Download All
```

---

# 9. Screen 9 — Export Center

## Purpose
Allow final file downloads.

## Page Title
**Export Generated Plan**

## Export Options

```text
Download Year-Wise Mining Plan PDF
Download Progressive Mine Closure Plan PDF
Download Conceptual Plan PDF
Download Alternative Comparison PDF
Download KML
Download KMZ
Download GeoJSON
Download Excel Quantity Table
Download Engineering Report PDF
Download ZIP Package
```

## ZIP Structure

```text
Mining_Plan_Output.zip
├── Reports/
│   ├── Engineering_Report.pdf
│   └── Alternative_Comparison.pdf
├── Maps/
│   ├── Year_Wise_Mining_Plan.pdf
│   ├── Progressive_Mine_Closure_Plan.pdf
│   ├── Conceptual_Plan.pdf
│   └── Environment_Plan.pdf
├── GIS/
│   ├── Year_Wise_Pits.kml
│   ├── All_Layers.geojson
│   └── Project.kmz
├── Excel/
│   └── Quantity_Table.xlsx
└── Metadata/
    ├── project_details.json
    ├── engineering_inputs.json
    └── validation_warnings.json
```

---

# 10. Main JSON Data Model

Use this structure internally:

```json
{
  "project_details": {
    "project_name": "Haripura Limestone Block TKSB-18",
    "applicant_name": "M/s. Example",
    "mineral": "Limestone",
    "village": "Haripura",
    "tehsil": "Kheenvsar",
    "district": "Nagaur",
    "state": "Rajasthan",
    "area_ha": 4.8,
    "map_type": "surface_plan",
    "scale": "1:1000",
    "survey_date": "2025-03-10",
    "plan_period_years": 5
  },
  "uploaded_files": [],
  "digitized_layers": [],
  "engineering_inputs": {},
  "selected_alternatives": [
    "base",
    "conservative",
    "aggressive"
  ],
  "generated_plans": [],
  "quantity_tables": [],
  "validation_warnings": []
}
```

---

# 11. Claude Code / Antigravity Build Prompt

Use this complete prompt to build the interface:

```text
You are a senior full-stack GIS application developer and mining planning software architect.

Build a web application called "Mining Plan Generator".

The interface flow must be:

1. First screen asks basic project details:
   - project_name
   - applicant_name
   - mineral
   - village
   - tehsil
   - district
   - state
   - area_ha
   - map_type
   - scale
   - survey_date
   - plan_period_years

Use this default sample:
{
  "project_name": "Haripura Limestone Block TKSB-18",
  "applicant_name": "M/s. Example",
  "mineral": "Limestone",
  "village": "Haripura",
  "tehsil": "Kheenvsar",
  "district": "Nagaur",
  "state": "Rajasthan",
  "area_ha": 4.8,
  "map_type": "surface_plan",
  "scale": "1:1000"
}

2. Next screen allows upload of plan files:
   - PDF
   - KML
   - KMZ
   - GeoJSON
   - JPG
   - PNG
   - Excel
   - CSV

The upload screen must have separate upload cards for:
   - Surface Plan
   - Surface Geological Plan
   - Geological Section
   - Progressive Mine Closure Plan
   - Conceptual Plan
   - Environment Plan
   - Key Plan
   - Financial Assurance Plan
   - Borehole Data
   - Chemical Analysis
   - Production Data

3. After upload, show PDF/image/KML preview.
For PDF, show page thumbnails and allow page selection.
For KML/KMZ/GeoJSON, parse layers and show them on the map.

4. Add a layer extraction/digitization screen where user can mark:
   - Lease Boundary
   - 7.5 m Statutory Barrier
   - Road/Rasta
   - Contour
   - Borehole
   - Geological Zone
   - Ultimate Pit Limit
   - Year-wise Pit
   - OB Dump
   - Topsoil Yard
   - Backfill
   - Plantation
   - Haul Road
   - Garland Drain
   - Settling Tank
   - Fencing
   - Retaining Wall
   - Water Reservoir

5. Ask engineering inputs:
   - annual_production_target_tonnes
   - approved_capacity_tonnes_per_year
   - bench_height_m
   - bench_width_m
   - face_slope_degree
   - overall_pit_slope_degree
   - haul_road_width_m
   - haul_road_gradient
   - bulk_density_t_per_m3
   - topsoil_thickness_m
   - overburden_thickness_m
   - mineral_recovery_percent
   - working_days_per_year
   - machinery details
   - chemical analysis fields

6. Ask alternative choice with cards:
   - Conservative
   - Base
   - Aggressive
   - Low-Waste / Backfill Priority
   - Environment-Sensitive
   - Cost-Optimized
   - Grade-Blending
   - Minimum-Disturbance

7. When user clicks Generate Plan:
Generate 1-year to 5-year mining plan layers:
   - Year I Pit
   - Year II Pit
   - Year III Pit
   - Year IV Pit
   - Year V Pit
   - Year-wise OB
   - Year-wise Topsoil
   - Year-wise Backfill
   - Year-wise Plantation
   - Haul Road
   - Drainage
   - Settling Tank
   - Mineral Stack Yard

8. Generate quantity tables:
   - pit area
   - excavation volume
   - mineral tonnes
   - saleable tonnes
   - OB quantity
   - topsoil quantity
   - backfill quantity
   - plantation area
   - stripping ratio

9. Add review screen:
The user must be able to check the generated plan, toggle layers, select alternative, select year, edit polygons, move labels and recalculate quantities.

10. Add Convert to PDF option:
After checking, user clicks "Convert to PDF".
The PDF must look like uploaded statutory mining plans:
   - A3 landscape
   - north arrow
   - scale bar
   - coordinate grid
   - legend/index
   - title block
   - certification box
   - year-wise color coding
   - lease boundary
   - 7.5 m statutory barrier
   - pit/OB/topsoil/backfill/plantation layers

11. Add export center:
User can download:
   - Year-Wise Mining Plan PDF
   - Progressive Mine Closure Plan PDF
   - Conceptual Plan PDF
   - KML
   - KMZ
   - GeoJSON
   - Excel quantity table
   - Engineering Report PDF
   - ZIP package

Technical stack:
Frontend:
- React or Next.js
- TypeScript
- Tailwind CSS
- Leaflet or MapLibre GL
- Turf.js
- PDF.js

Backend:
- Python FastAPI
- Shapely
- GeoPandas
- PyProj
- Pandas
- OpenPyXL
- ReportLab or WeasyPrint
- simplekml
- zipfile

Important:
This should not be a dummy UI only.
Make functional upload, map preview, layer drawing, quantity calculation and PDF export.
If automatic extraction is difficult, first build manual digitization properly.
Use clean modern UI with stepper navigation:
Step 1: Project Details
Step 2: Upload Plans
Step 3: Extract Layers
Step 4: Engineering Inputs
Step 5: Alternatives
Step 6: Generate Plan
Step 7: Review/Edit
Step 8: Convert to PDF
Step 9: Export

Add validation:
- No pit outside lease boundary.
- No pit inside statutory barrier unless override.
- No dump overlapping active pit.
- Production must not exceed approved capacity.
- Missing technical data must be shown as warning.
- Assumed values must be marked as "ASSUMED — NEEDS VALIDATION".

Add statutory disclaimer:
Generated output is conceptual and must be reviewed and signed by qualified mining engineer/RQP before official use.

Deliver:
- Full working project
- README.md setup guide
- CLAUDE.md
- sample project JSON
- sample PDF map export
- sample Excel quantity output
```

---

# 12. Visual Style Requirements

## UI Theme

Use a professional mining/GIS theme:

```text
Primary color: Deep navy / charcoal
Accent color: mining orange / safety yellow
Map background: light grey
Cards: white with soft shadow
Status warnings: amber
Errors: red
Success: green
```

## UI Design
The interface should feel like engineering software, not a normal form website.

Use:

```text
Stepper navigation
Left sidebar
Large map workspace
Layer panel
Professional form cards
Download buttons
Validation badges
Preview modal
```

---

# 13. Minimum Working Prototype Requirement

The first version must at least do this:

```text
1. Take project details.
2. Upload one PDF/image map.
3. Allow manual drawing of lease boundary.
4. Allow manual drawing of Year I to Year V pit polygons.
5. Ask engineering inputs.
6. Generate quantity table.
7. Select at least 3 alternatives.
8. Create a PDF map with legend, north arrow, scale bar and title block.
9. Export KML/GeoJSON.
10. Export Excel table.
```

---

# 14. Final Note

The most important part of this application is the **review/edit before PDF export**.

The software should generate the plan, but the mining engineer must be able to correct:
- Pit boundary
- Year-wise sequence
- Dump area
- Topsoil yard
- Haul road
- Backfilling
- Plantation
- Labels
- Quantities

Only after this review should the user click:

```text
Convert to PDF
```
