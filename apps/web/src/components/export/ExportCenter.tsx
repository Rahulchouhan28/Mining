"use client";

import { Archive, BarChart3, BookOpen, Download, FileCode2, FileSpreadsheet, FileText, Globe } from "lucide-react";
import type { Alternative } from "@/lib/types";

interface Props {
  slug: string;
  alternatives: Alternative[];
  planYears: number;
}

interface ExportLinkProps {
  href: string;
  icon: React.ReactNode;
  title: string;
  blurb: string;
  download?: string;
}

function ExportLink({ href, icon, title, blurb, download }: ExportLinkProps) {
  return (
    <a
      href={href}
      download={download ?? true}
      className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 transition hover:border-amber-400 hover:shadow"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-amber-100 text-amber-700">
        {icon}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          {title}
          <Download className="h-3.5 w-3.5 text-slate-400" />
        </div>
        <p className="mt-1 text-xs text-slate-600">{blurb}</p>
      </div>
    </a>
  );
}

export function ExportCenter({ slug, alternatives, planYears }: Props) {
  const PLATE_LETTERS = ["", "A", "B", "C", "D", "E"];
  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Per-Year Statutory Plates
        </h3>
        <p className="mb-3 text-xs text-slate-600">
          One A3 plate per year, modelled on the statutory reference. Each plate shows the year&apos;s
          mine working highlighted, faint outlines of prior years, this year&apos;s cumulative OB / topsoil
          / plantation, and a <em>DIRECTION OF NEXT YEAR</em> arrow.
        </p>
        {alternatives.map((alt) => (
          <div key={alt} className="mb-4">
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600">{alt}</div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-5">
              {Array.from({ length: planYears }, (_, i) => i + 1).map((y) => (
                <ExportLink
                  key={y}
                  href={`/api/projects/${slug}/export/year-plate?alternative=${alt}&year=${y}&paper=A3&orientation=landscape&scale=1000`}
                  icon={<FileText className="h-5 w-5" />}
                  title={`Year ${y} — Plate 5${PLATE_LETTERS[y]}`}
                  blurb=""
                />
              ))}
              <ExportLink
                href={`/api/projects/${slug}/export/year-plates-zip?alternative=${alt}`}
                icon={<Archive className="h-5 w-5" />}
                title="All years (ZIP)"
                blurb=""
              />
            </div>
          </div>
        ))}
      </section>

      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          AutoCAD DXF (R2010, units = meters, UTM 43 N)
        </h3>
        <p className="mb-3 text-xs text-slate-600">
          Open directly in AutoCAD, BricsCAD, LibreCAD, QCAD, ZWCAD or ProgeCAD. Layers named per
          Indian RQP convention (<code>LEASE_BOUNDARY</code>, <code>BARRIER_7_5M</code>,{" "}
          <code>YEAR_N_WORKING</code>, <code>OB_DUMP_YN</code>, <code>TOPSOIL_YN</code>,{" "}
          <code>PLANTATION_YN</code>, etc.). DXF is the AutoCAD-native exchange format and is
          accepted by Indian mining regulators.
        </p>
        {alternatives.map((alt) => (
          <div key={`dxf-${alt}`} className="mb-4">
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600">{alt}</div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-5">
              {Array.from({ length: planYears }, (_, i) => i + 1).map((y) => (
                <ExportLink
                  key={y}
                  href={`/api/projects/${slug}/export/year-dxf?alternative=${alt}&year=${y}`}
                  icon={<FileCode2 className="h-5 w-5" />}
                  title={`Year ${y} DXF`}
                  blurb=""
                />
              ))}
              <ExportLink
                href={`/api/projects/${slug}/export/year-dxfs-zip?alternative=${alt}`}
                icon={<Archive className="h-5 w-5" />}
                title="All DXFs (ZIP)"
                blurb=""
              />
            </div>
          </div>
        ))}
      </section>

      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Overview Plates</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {alternatives.map((alt) => (
            <ExportLink
              key={alt}
              href={`/api/projects/${slug}/export/pdf?alternative=${alt}&plate_type=year_wise_mining_plan&paper=A3&orientation=landscape&scale=1000`}
              icon={<FileText className="h-5 w-5" />}
              title={`Year-Wise Overview (${alt})`}
              blurb="A3 landscape, all years on one map, year-coded pit polygons."
            />
          ))}
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Comparison &amp; Report</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ExportLink
            href={`/api/projects/${slug}/export/comparison-pdf`}
            icon={<BarChart3 className="h-5 w-5" />}
            title="Alternative comparison plate"
            blurb="All approaches side-by-side on one A3 sheet with a totals delta table."
          />
          <ExportLink
            href={`/api/projects/${slug}/export/report-pdf`}
            icon={<BookOpen className="h-5 w-5" />}
            title="Engineering report (A4)"
            blurb="Multi-page narrative: project details, inputs (with ASSUMED markers), per-approach quantity tables, formulas, validation warnings, certification."
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">GIS</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ExportLink
            href={`/api/projects/${slug}/export/geojson`}
            icon={<Globe className="h-5 w-5" />}
            title="GeoJSON"
            blurb="All digitized layers as a single FeatureCollection (WGS84)."
          />
          <ExportLink
            href={`/api/projects/${slug}/export/kml`}
            icon={<Globe className="h-5 w-5" />}
            title="KML"
            blurb="Digitized + generated layers, color-coded by layer type. Opens in Google Earth."
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Data</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ExportLink
            href={`/api/projects/${slug}/export/excel`}
            icon={<FileSpreadsheet className="h-5 w-5" />}
            title="Quantity Table (Excel)"
            blurb="One sheet per alternative with year-wise pit area, mineral, saleable, OB, topsoil, backfill, stripping ratio."
          />
          <ExportLink
            href={`/api/projects/${slug}/export/zip`}
            icon={<Archive className="h-5 w-5" />}
            title="ZIP package"
            blurb="Maps, GIS, Excel, and metadata in a single zip. Matches the spec Section 9 layout."
          />
        </div>
      </section>

      <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
        All exports carry the certification clause. They are conceptual outputs and must be
        signed by a qualified mining engineer / RQP before any statutory submission.
      </p>
    </div>
  );
}
