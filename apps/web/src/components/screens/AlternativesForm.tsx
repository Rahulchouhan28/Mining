"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { CheckCircle2, Circle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Alternative, MiningPlanProject } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  slug: string;
  initial: Alternative[];
}

interface AltCard {
  key: Alternative;
  title: string;
  blurb: string;
  enabled: boolean;
}

const CARDS: AltCard[] = [
  { key: "base",                  title: "B — Base",                 blurb: "Balanced plan following uploaded layout and standard five-year development.", enabled: true },
  { key: "conservative",          title: "A — Conservative",         blurb: "Lower production, minimum disturbance, slow pit advancement.", enabled: true },
  { key: "aggressive",            title: "C — Aggressive",           blurb: "Maximum permitted production, faster excavation, larger machinery requirement.", enabled: true },
  { key: "low_waste",             title: "D — Low-Waste / Backfill", blurb: "Minimizes external overburden dump and prioritizes backfilling.", enabled: false },
  { key: "environment_sensitive", title: "E — Environment-Sensitive",blurb: "Avoids tanks, habitation, roads, temples, electric lines.", enabled: false },
  { key: "cost_optimized",        title: "F — Cost-Optimized",       blurb: "Minimizes haul distance, road length, machinery movement and cost.", enabled: false },
  { key: "grade_blending",        title: "G — Grade-Blending",       blurb: "Plans excavation based on grade zones and buyer specification.", enabled: false },
  { key: "minimum_disturbance",   title: "H — Minimum-Disturbance",  blurb: "Minimizes disturbed area and delays sensitive land disturbance.", enabled: false },
];

export function AlternativesForm({ slug, initial }: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<Alternative>>(
    new Set(initial.length ? initial : ["base", "conservative", "aggressive"]),
  );
  const [pending, startTransition] = useTransition();
  const [err, setErr] = useState<string | null>(null);

  function toggle(key: Alternative, enabled: boolean) {
    if (!enabled) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  function generate() {
    if (selected.size === 0) {
      setErr("Pick at least one alternative.");
      return;
    }
    startTransition(async () => {
      setErr(null);
      try {
        const cur = (await (await fetch(`/api/projects/${slug}`)).json()) as MiningPlanProject;
        const merged: MiningPlanProject = { ...cur, selected_alternatives: [...selected] };
        const put = await fetch(`/api/projects/${slug}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(merged),
        });
        if (!put.ok) throw new Error(`${put.status} ${await put.text()}`);
        const gen = await fetch(`/api/projects/${slug}/generate`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ alternatives: [...selected] }),
        });
        if (!gen.ok) throw new Error(`${gen.status} ${await gen.text()}`);
        router.push(`/project/${slug}/6`);
        router.refresh();
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Failed to start generation");
      }
    });
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((c) => {
          const active = selected.has(c.key);
          return (
            <button
              type="button"
              key={c.key}
              disabled={!c.enabled}
              onClick={() => toggle(c.key, c.enabled)}
              className={cn(
                "relative rounded-lg border p-4 text-left transition-all",
                c.enabled
                  ? active
                    ? "border-amber-500 bg-amber-50 shadow-sm"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
                  : "cursor-not-allowed border-slate-200 bg-slate-50 opacity-60",
              )}
            >
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-900">{c.title}</div>
                {active ? (
                  <CheckCircle2 className="h-5 w-5 text-amber-500" />
                ) : (
                  <Circle className="h-5 w-5 text-slate-300" />
                )}
              </div>
              <p className="text-xs text-slate-600">{c.blurb}</p>
              {!c.enabled && (
                <p className="mt-2 text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Coming in v2
                </p>
              )}
            </button>
          );
        })}
      </div>

      {err && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {err}
        </p>
      )}

      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
        <div className="text-xs text-slate-600">
          {selected.size} alternative{selected.size === 1 ? "" : "s"} selected
        </div>
        <Button type="button" variant="primary" disabled={pending} onClick={generate}>
          <Sparkles className="h-4 w-4" />
          {pending ? "Generating…" : "Generate Plan"}
        </Button>
      </div>
    </div>
  );
}
