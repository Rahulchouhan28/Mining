"use client";

import dynamic from "next/dynamic";
import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ChevronDown, FileDown, Info, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type {
  Alternative,
  EngineeringInputs,
  FeatureCollection,
  MiningPlanProject,
  ValidationWarning,
} from "@/lib/types";

const LeafletEditor = dynamic(() => import("@/components/digitize/LeafletEditor"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      Loading map…
    </div>
  ),
});

const SEVERITY_ICON = {
  error: <AlertTriangle className="h-3.5 w-3.5 text-red-600" />,
  warning: <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />,
  info: <Info className="h-3.5 w-3.5 text-sky-600" />,
} as const;

interface Props {
  slug: string;
  project: MiningPlanProject;
}

type YearView = "all" | 1 | 2 | 3 | 4 | 5;

export function AutoPlanScreen({ slug, project }: Props) {
  const router = useRouter();
  const alternatives: Alternative[] = project.selected_alternatives?.length
    ? project.selected_alternatives
    : ["base", "conservative", "aggressive"];
  const [activeAlt, setActiveAlt] = useState<Alternative>(alternatives[0]);
  const planYears = Math.min(5, Math.max(1, project.project_details.plan_period_years ?? 5));
  const [activeYear, setActiveYear] = useState<YearView>(1);
  const [editOpen, setEditOpen] = useState(false);
  const [regenerating, startRegen] = useTransition();
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Editable subset of engineering inputs
  const ei = project.engineering_inputs ?? {};
  const [form, setForm] = useState({
    annual_production_target_tonnes: ei.production?.annual_production_target_tonnes ?? 50000,
    bench_height_m: ei.bench?.bench_height_m ?? 6,
    bulk_density_t_per_m3: ei.mineral_waste?.bulk_density_t_per_m3 ?? 2.4,
    mineral_recovery_percent: ei.mineral_waste?.mineral_recovery_percent ?? 90,
    plan_period_years: project.project_details.plan_period_years ?? 5,
  });

  const layers: FeatureCollection = useMemo(() => {
    const plan = project.generated_plans?.find((p) => p.alternative === activeAlt);
    const lease = (project.digitized_layers?.features ?? []).filter(
      (f) => f.properties.layer_type === "lease_boundary",
    );
    const generated = plan?.features.features ?? [];
    if (activeYear === "all") {
      // Overview: keep year_pit per year, but for OB/topsoil/plantation only
      // keep the year=plan_years feature (final cumulative state).
      const finalFeatures = generated.filter((f) => {
        const yr = f.properties.year;
        const lt = f.properties.layer_type;
        if (["overburden_dump", "topsoil_stack", "plantation"].includes(lt) && typeof yr === "number") {
          return yr === planYears;
        }
        return true;
      });
      return { type: "FeatureCollection", features: [...lease, ...finalFeatures] };
    }
    // Per-year: drop other-year features for year-tagged layers; keep
    // always-on layers (lease, barrier, ult pit, haul road, boreholes, etc.).
    const YEAR_TAGGED = new Set(["year_pit", "overburden_dump", "topsoil_stack", "plantation"]);
    const filtered = generated.filter((f) => {
      const lt = f.properties.layer_type;
      const yr = f.properties.year;
      if (YEAR_TAGGED.has(lt)) return yr === activeYear;
      return true;
    });
    return { type: "FeatureCollection", features: [...lease, ...filtered] };
  }, [project, activeAlt, activeYear, planYears]);

  const quantity = project.quantity_tables?.find((q) => q.alternative === activeAlt);
  const altWarnings = (project.validation_warnings ?? []).filter(
    (w) => !w.alternative || w.alternative === activeAlt,
  );

  function applyAndRegenerate() {
    startRegen(async () => {
      setError(null);
      try {
        const cur = (await (await fetch(`/api/projects/${slug}`)).json()) as MiningPlanProject;
        const newEi: EngineeringInputs = {
          ...cur.engineering_inputs,
          production: {
            ...cur.engineering_inputs?.production,
            annual_production_target_tonnes: form.annual_production_target_tonnes,
          },
          bench: { ...cur.engineering_inputs?.bench, bench_height_m: form.bench_height_m },
          mineral_waste: {
            ...cur.engineering_inputs?.mineral_waste,
            bulk_density_t_per_m3: form.bulk_density_t_per_m3,
            mineral_recovery_percent: form.mineral_recovery_percent,
          },
        };
        const updated: MiningPlanProject = {
          ...cur,
          engineering_inputs: newEi,
          project_details: { ...cur.project_details, plan_period_years: form.plan_period_years },
        };
        const put = await fetch(`/api/projects/${slug}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(updated),
        });
        if (!put.ok) throw new Error(`${put.status} ${await put.text()}`);
        const gen = await fetch(`/api/projects/${slug}/generate`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ alternatives }),
        });
        if (!gen.ok) throw new Error(`${gen.status} ${await gen.text()}`);
        router.refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Re-generate failed");
      }
    });
  }

  async function downloadPdf() {
    setError(null);
    setDownloading(true);
    try {
      let url: string;
      let filename: string;
      if (activeYear === "all") {
        const params = new URLSearchParams({
          alternative: activeAlt,
          plate_type: "year_wise_mining_plan",
          paper: "A3", orientation: "landscape", scale: "1000",
        });
        url = `/api/projects/${slug}/export/pdf?${params}`;
        filename = `${slug}_${activeAlt}_year_wise_overview.pdf`;
      } else {
        const letter = ["", "A", "B", "C", "D", "E"][activeYear];
        const params = new URLSearchParams({
          alternative: activeAlt, year: String(activeYear),
          paper: "A3", orientation: "landscape", scale: "1000",
        });
        url = `/api/projects/${slug}/export/year-plate?${params}`;
        filename = `${slug}_${activeAlt}_year_${activeYear}_development_plan_5${letter}.pdf`;
      }
      const r = await fetch(url);
      if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
      const blob = await r.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(blobUrl);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF download failed");
    } finally {
      setDownloading(false);
    }
  }

  if (!project.generated_plans || project.generated_plans.length === 0) {
    return (
      <div className="mx-auto max-w-2xl rounded-lg border border-dashed border-amber-300 bg-amber-50 p-8 text-center">
        <Sparkles className="mx-auto h-8 w-8 text-amber-500" />
        <p className="mt-3 text-sm text-amber-900">
          No plan generated yet. Go back to step 2 and click <em>Generate Year-Wise Plan</em>.
        </p>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col gap-4 pb-20">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Approach</span>
          {alternatives.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => setActiveAlt(a)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium capitalize transition",
                a === activeAlt ? "bg-amber-500 text-slate-950" : "bg-slate-100 text-slate-700 hover:bg-slate-200",
              )}
            >
              {a.replace("_", " ")}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Year</span>
          {Array.from({ length: planYears }, (_, i) => (i + 1) as 1 | 2 | 3 | 4 | 5).map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => setActiveYear(y)}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-xs font-medium transition",
                y === activeYear ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200",
              )}
            >
              Year {y}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setActiveYear("all")}
            className={cn(
              "rounded-md px-2.5 py-1.5 text-xs font-medium transition",
              activeYear === "all" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200",
            )}
          >
            All / overview
          </button>
        </div>
        {quantity && (
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-600">
            <Stat label="Years" value={quantity.rows.length.toString()} />
            <Stat label="Total saleable" value={`${(quantity.rows.reduce((a, r) => a + (r.saleable_tonnes ?? 0), 0) / 1000).toFixed(1)} kt`} />
            <Stat label="Cumulative pit" value={`${(quantity.rows.reduce((a, r) => a + (r.pit_area_m2 ?? 0), 0) / 10000).toFixed(3)} ha`} />
          </div>
        )}
      </div>

      <div className="min-h-[55vh] overflow-hidden rounded-lg">
        <LeafletEditor initial={layers} onChange={() => { /* read-only here */ }} />
      </div>

      {quantity && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Year-wise quantities — {activeAlt}
          </h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-1 pr-2">Yr</th>
                <th className="py-1 pr-2 text-right">Pit area (m²)</th>
                <th className="py-1 pr-2 text-right">Mineral (t)</th>
                <th className="py-1 pr-2 text-right">Saleable (t)</th>
                <th className="py-1 pr-2 text-right">OB (m³)</th>
                <th className="py-1 pr-2 text-right">Topsoil (m³)</th>
                <th className="py-1 pr-2 text-right">Backfill (m³)</th>
                <th className="py-1 pr-2 text-right">SR</th>
              </tr>
            </thead>
            <tbody className="text-slate-700">
              {quantity.rows.map((r) => (
                <tr key={r.year} className="border-t border-slate-100">
                  <td className="py-1 pr-2 font-medium">{r.year}</td>
                  <td className="py-1 pr-2 text-right">{Math.round(r.pit_area_m2 ?? 0).toLocaleString()}</td>
                  <td className="py-1 pr-2 text-right">{Math.round(r.mineral_tonnes ?? 0).toLocaleString()}</td>
                  <td className="py-1 pr-2 text-right">{Math.round(r.saleable_tonnes ?? 0).toLocaleString()}</td>
                  <td className="py-1 pr-2 text-right">{Math.round(r.overburden_m3 ?? 0).toLocaleString()}</td>
                  <td className="py-1 pr-2 text-right">{Math.round(r.topsoil_m3 ?? 0).toLocaleString()}</td>
                  <td className="py-1 pr-2 text-right">{Math.round(r.backfill_m3 ?? 0).toLocaleString()}</td>
                  <td className="py-1 pr-2 text-right">{(r.stripping_ratio ?? 0).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <details
        open={editOpen}
        onToggle={(e) => setEditOpen((e.target as HTMLDetailsElement).open)}
        className="rounded-lg border border-slate-200 bg-white"
      >
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-medium text-slate-900">
          <span>Adjust parameters &amp; re-generate</span>
          <ChevronDown className={cn("h-4 w-4 text-slate-500 transition-transform", editOpen && "rotate-180")} />
        </summary>
        <div className="grid grid-cols-1 gap-3 border-t border-slate-200 p-4 md:grid-cols-2 lg:grid-cols-3">
          <NumberInput label="Annual production target (t/y)" value={form.annual_production_target_tonnes}
            onChange={(v) => setForm((p) => ({ ...p, annual_production_target_tonnes: v }))} step={1000} />
          <NumberInput label="Bench height (m)" value={form.bench_height_m}
            onChange={(v) => setForm((p) => ({ ...p, bench_height_m: v }))} step={0.5} />
          <NumberInput label="Bulk density (t/m³)" value={form.bulk_density_t_per_m3}
            onChange={(v) => setForm((p) => ({ ...p, bulk_density_t_per_m3: v }))} step={0.05} />
          <NumberInput label="Mineral recovery (%)" value={form.mineral_recovery_percent}
            onChange={(v) => setForm((p) => ({ ...p, mineral_recovery_percent: v }))} step={1} />
          <div>
            <Label className="mb-1">Plan period (years)</Label>
            <select
              className="h-10 w-full rounded-md border border-slate-300 px-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
              value={form.plan_period_years}
              onChange={(e) => setForm((p) => ({ ...p, plan_period_years: Number(e.target.value) }))}
            >
              {[1, 2, 3, 4, 5].map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <Button type="button" variant="secondary" disabled={regenerating} onClick={applyAndRegenerate} className="w-full">
              <RefreshCw className={cn("h-4 w-4", regenerating && "animate-spin")} />
              {regenerating ? "Regenerating…" : "Apply &amp; Re-generate"}
            </Button>
          </div>
        </div>
      </details>

      {altWarnings.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Validation</h3>
          <ul className="space-y-1.5">
            {altWarnings.map((w: ValidationWarning, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
                {SEVERITY_ICON[w.severity]}
                <span>
                  <span className="font-mono text-[10px] text-slate-500">{w.code}</span>
                  <span className="ml-1.5">{w.message}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}

      <div className="fixed bottom-6 right-8 z-30">
        <Button
          type="button"
          variant="primary"
          size="lg"
          disabled={downloading}
          onClick={downloadPdf}
          className="shadow-xl"
        >
          {downloading ? <Loader2 className="h-5 w-5 animate-spin" /> : <FileDown className="h-5 w-5" />}
          {downloading
            ? "Generating PDF…"
            : activeYear === "all"
              ? `Convert overview to PDF (${activeAlt})`
              : `Convert Year ${activeYear} to PDF (${activeAlt})`}
        </Button>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-slate-100 px-2 py-1">
      <div className="text-[9px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="font-medium text-slate-900">{value}</div>
    </div>
  );
}

function NumberInput({ label, value, onChange, step }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div>
      <Label className="mb-1">{label}</Label>
      <Input
        type="number"
        step={step ?? 1}
        value={value}
        onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
      />
    </div>
  );
}
