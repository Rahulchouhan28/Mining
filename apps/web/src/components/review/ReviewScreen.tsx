"use client";

import dynamic from "next/dynamic";
import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, FileText, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LAYER_LABELS } from "@/components/digitize/LayerCatalog";
import type { Alternative, FeatureCollection, MiningPlanProject, LayerType } from "@/lib/types";

const LeafletEditor = dynamic(() => import("@/components/digitize/LeafletEditor"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      Loading map…
    </div>
  ),
});

interface Props {
  slug: string;
  project: MiningPlanProject;
}

type YearFilter = "all" | 1 | 2 | 3 | 4 | 5;

export function ReviewScreen({ slug, project }: Props) {
  const router = useRouter();
  const alternatives = project.selected_alternatives ?? [];
  const [activeAlt, setActiveAlt] = useState<Alternative>(alternatives[0] ?? "base");
  const [yearFilter, setYearFilter] = useState<YearFilter>("all");
  const [hidden, setHidden] = useState<Set<LayerType>>(new Set());
  const [approved, setApproved] = useState(false);
  const [saving, startSaving] = useTransition();
  const [msg, setMsg] = useState<string | null>(null);

  const layers: FeatureCollection = useMemo(() => {
    const plan = project.generated_plans?.find((p) => p.alternative === activeAlt);
    const userDigitized = (project.digitized_layers?.features ?? [])
      .filter((f) => f.properties.layer_type === "lease_boundary");
    const generated = plan?.features.features ?? [];
    const all = [...userDigitized, ...generated];
    const filtered = all.filter((f) => {
      if (hidden.has(f.properties.layer_type)) return false;
      if (yearFilter !== "all" && f.properties.layer_type === "year_pit") {
        return f.properties.year === yearFilter;
      }
      return true;
    });
    return { type: "FeatureCollection", features: filtered };
  }, [project, activeAlt, yearFilter, hidden]);

  const layerKeys = useMemo(() => {
    const plan = project.generated_plans?.find((p) => p.alternative === activeAlt);
    const types = new Set<LayerType>();
    for (const f of plan?.features.features ?? []) types.add(f.properties.layer_type);
    for (const f of project.digitized_layers?.features ?? []) types.add(f.properties.layer_type);
    return [...types];
  }, [project, activeAlt]);

  function persistEdits(fc: FeatureCollection) {
    // For v1 we only persist user-drawn layers (lease etc.) — generated layers are
    // re-derived. v2 will track manual edits to generated polygons separately.
    const userOnly = fc.features.filter((f) =>
      f.properties.layer_type === "lease_boundary" ||
      f.properties.layer_type === "statutory_barrier_7_5m" ||
      f.properties.layer_type === "ultimate_pit_limit"
    );
    void userOnly; // intentionally not persisted in v1 review
  }

  async function approveAndContinue() {
    if (!approved) {
      setMsg("Please tick the approval checkbox first.");
      return;
    }
    startSaving(async () => {
      try {
        // Mark approval in the project metadata
        const cur = await (await fetch(`/api/projects/${slug}`)).json();
        cur.review_approved = { approved_at: new Date().toISOString(), by: "user" };
        const r = await fetch(`/api/projects/${slug}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(cur),
        });
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        router.push(`/project/${slug}/8`);
        router.refresh();
      } catch (e) {
        setMsg(e instanceof Error ? e.message : "Save failed");
      }
    });
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-2.5">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">Alternative</div>
        <div className="flex flex-wrap gap-1">
          {alternatives.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => setActiveAlt(a)}
              className={cn(
                "rounded px-3 py-1.5 text-xs font-medium",
                a === activeAlt ? "bg-amber-500 text-slate-950" : "bg-slate-100 text-slate-700 hover:bg-slate-200",
              )}
            >
              {a}
            </button>
          ))}
        </div>
        <div className="mx-2 h-5 w-px bg-slate-200" />
        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">Years</div>
        <div className="flex flex-wrap gap-1">
          {(["all", 1, 2, 3, 4, 5] as YearFilter[]).map((y) => (
            <button
              key={String(y)}
              type="button"
              onClick={() => setYearFilter(y)}
              className={cn(
                "rounded px-2.5 py-1.5 text-xs font-medium",
                y === yearFilter ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200",
              )}
            >
              {y === "all" ? "All" : `Yr ${y}`}
            </button>
          ))}
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-[1fr_280px]">
        <div className="min-h-[55vh] overflow-hidden rounded-lg">
          <LeafletEditor
            initial={layers}
            onChange={persistEdits}
          />
        </div>

        <aside className="flex flex-col gap-3">
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Layers
            </h3>
            <ul className="space-y-1 text-xs">
              {layerKeys.map((k) => {
                const isHidden = hidden.has(k);
                return (
                  <li key={k}>
                    <button
                      type="button"
                      onClick={() => setHidden((prev) => {
                        const next = new Set(prev);
                        if (next.has(k)) next.delete(k); else next.add(k);
                        return next;
                      })}
                      className="flex w-full items-center justify-between rounded px-2 py-1 text-left text-slate-700 hover:bg-slate-50"
                    >
                      <span>{LAYER_LABELS[k]}</span>
                      {isHidden ? <EyeOff className="h-3.5 w-3.5 text-slate-400" /> : <Eye className="h-3.5 w-3.5 text-amber-500" />}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <label className="flex items-start gap-2 text-xs text-amber-900">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-amber-400 text-amber-500 focus:ring-amber-500"
                checked={approved}
                onChange={(e) => setApproved(e.target.checked)}
              />
              <span>
                I have reviewed the generated plan and understand that final statutory submission
                must be verified by a qualified mining engineer / RQP / competent person.
              </span>
            </label>
          </div>

          <div className="space-y-2">
            <Button
              type="button"
              variant="primary"
              disabled={!approved || saving}
              onClick={approveAndContinue}
              className="w-full"
            >
              <ShieldCheck className="h-4 w-4" />
              {saving ? "Saving…" : "Approve & Continue"}
            </Button>
            <Link href={`/project/${slug}/8`}>
              <Button type="button" variant="outline" className="w-full" disabled={!approved}>
                <FileText className="h-4 w-4" />
                Skip to PDF Composer
              </Button>
            </Link>
          </div>

          {msg && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-900">
              {msg}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
