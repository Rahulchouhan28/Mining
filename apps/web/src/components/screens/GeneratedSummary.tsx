"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Info, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { MiningPlanProject } from "@/lib/types";

interface Props {
  slug: string;
  project: MiningPlanProject;
}

const SEVERITY_ICON = {
  error: <AlertTriangle className="h-4 w-4 text-red-600" />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-600" />,
  info: <Info className="h-4 w-4 text-sky-600" />,
} as const;

export function GeneratedSummary({ slug, project }: Props) {
  const router = useRouter();
  const [busy, startBusy] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const alternatives = project.selected_alternatives ?? [];

  function regenerate() {
    startBusy(async () => {
      setError(null);
      try {
        const r = await fetch(`/api/projects/${slug}/generate`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ alternatives }),
        });
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        router.refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Regenerate failed");
      }
    });
  }

  if (!project.generated_plans || project.generated_plans.length === 0) {
    return (
      <div className="mx-auto max-w-2xl rounded-lg border border-dashed border-amber-300 bg-amber-50 p-8 text-center">
        <Sparkles className="mx-auto h-8 w-8 text-amber-500" />
        <p className="mt-3 text-sm text-amber-800">
          No plan generated yet. Go back to step 5 and click <em>Generate Plan</em>.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-emerald-900">
          <CheckCircle2 className="h-4 w-4" />
          {project.generated_plans.length} plan{project.generated_plans.length === 1 ? "" : "s"} generated for {alternatives.join(", ")}.
        </div>
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={regenerate}>
          <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
          {busy ? "Regenerating…" : "Regenerate"}
        </Button>
      </div>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(project.quantity_tables ?? []).map((qt) => {
          const total = qt.rows.reduce(
            (acc, r) => {
              acc.saleable += r.saleable_tonnes ?? 0;
              acc.ob += r.overburden_m3 ?? 0;
              acc.area += r.pit_area_m2 ?? 0;
              return acc;
            },
            { saleable: 0, ob: 0, area: 0 },
          );
          return (
            <div key={qt.alternative} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wider text-amber-600">
                {qt.alternative}
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-700">
                <Stat label="Years" value={qt.rows.length.toString()} />
                <Stat label="Total saleable" value={`${(total.saleable / 1000).toFixed(1)} kt`} />
                <Stat label="Cumulative pit" value={`${(total.area / 10000).toFixed(3)} ha`} />
                <Stat label="Total OB" value={`${(total.ob / 1000).toFixed(1)} k m³`} />
              </div>
              <table className="mt-3 w-full text-[11px]">
                <thead>
                  <tr className="text-left text-slate-500">
                    <th className="py-1 pr-2">Yr</th>
                    <th className="py-1 pr-2 text-right">Pit m²</th>
                    <th className="py-1 pr-2 text-right">Saleable t</th>
                    <th className="py-1 pr-2 text-right">OB m³</th>
                  </tr>
                </thead>
                <tbody className="text-slate-700">
                  {qt.rows.map((r) => (
                    <tr key={r.year} className="border-t border-slate-100">
                      <td className="py-1 pr-2">{r.year}</td>
                      <td className="py-1 pr-2 text-right">{Math.round(r.pit_area_m2 ?? 0).toLocaleString()}</td>
                      <td className="py-1 pr-2 text-right">{Math.round(r.saleable_tonnes ?? 0).toLocaleString()}</td>
                      <td className="py-1 pr-2 text-right">{Math.round(r.overburden_m3 ?? 0).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>

      {project.validation_warnings && project.validation_warnings.length > 0 && (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Validation
          </h3>
          <ul className="space-y-1.5">
            {project.validation_warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
                {SEVERITY_ICON[w.severity]}
                <span>
                  <span className="font-mono text-[10px] text-slate-500">{w.code}</span>
                  {w.alternative && <span className="ml-1 text-[10px] text-slate-400">[{w.alternative}]</span>}
                  <span className="ml-1.5">{w.message}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-slate-50 px-2 py-1">
      <div className="text-[9px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="font-medium text-slate-900">{value}</div>
    </div>
  );
}
