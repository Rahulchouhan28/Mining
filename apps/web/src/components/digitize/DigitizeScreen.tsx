"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { FeatureCollection, MiningPlanProject } from "@/lib/types";
import { LAYER_LABELS } from "./LayerCatalog";

const LeafletEditor = dynamic(() => import("./LeafletEditor"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      Loading map editor…
    </div>
  ),
});

interface Props {
  slug: string;
  project: MiningPlanProject;
}

export function DigitizeScreen({ slug, project }: Props) {
  const router = useRouter();
  const [fc, setFc] = useState<FeatureCollection>(
    project.digitized_layers ?? { type: "FeatureCollection", features: [] },
  );
  const [saving, startSaving] = useTransition();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // Underlay state — simple 2-corner georeferencing for the most-recent surface plan upload.
  const surfaceUpload = useMemo(
    () => (project.uploaded_files ?? []).find((f) => f.category === "surface_plan"),
    [project.uploaded_files],
  );
  const [nw, setNw] = useState({ lat: "", lng: "" });
  const [se, setSe] = useState({ lat: "", lng: "" });
  const [underlayActive, setUnderlayActive] = useState(false);

  const underlayBounds = useMemo(() => {
    const nwLat = parseFloat(nw.lat), nwLng = parseFloat(nw.lng);
    const seLat = parseFloat(se.lat), seLng = parseFloat(se.lng);
    if ([nwLat, nwLng, seLat, seLng].some((v) => Number.isNaN(v))) return null;
    return [
      [seLat, nwLng],
      [nwLat, seLng],
    ] as [[number, number], [number, number]];
  }, [nw, se]);

  // Generate 7.5 m statutory barrier from the lease (server-side, UTM 43 N)
  const onLeaseSet = useCallback(
    async (poly: GeoJSON.Polygon) => {
      setBusy(true);
      setMsg(null);
      try {
        const res = await fetch("/api/gis/buffer", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ geometry: poly, distance_m: -7.5 }),
        });
        if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
        const data = (await res.json()) as { geometry: GeoJSON.Geometry | null; area_m2: number };
        if (data.geometry) {
          setFc((prev) => {
            const others = prev.features.filter(
              (f) => f.properties.layer_type !== "statutory_barrier_7_5m",
            );
            return {
              type: "FeatureCollection",
              features: [
                ...others,
                {
                  type: "Feature",
                  geometry: data.geometry!,
                  properties: {
                    layer_type: "statutory_barrier_7_5m",
                    label: "7.5 m statutory barrier",
                    color: "#dc2626",
                    locked: true,
                  },
                },
              ],
            };
          });
          setMsg(`Auto-generated 7.5 m statutory barrier (available pit area inside barrier: ${Math.round(data.area_m2).toLocaleString()} m²).`);
        }
      } catch (e) {
        setMsg(e instanceof Error ? `Barrier failed: ${e.message}` : "Barrier failed");
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  function save() {
    startSaving(async () => {
      setMsg(null);
      try {
        const res = await fetch(`/api/projects/${slug}`);
        if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
        const cur = (await res.json()) as MiningPlanProject;
        const merged: MiningPlanProject = { ...cur, digitized_layers: fc };
        const put = await fetch(`/api/projects/${slug}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(merged),
        });
        if (!put.ok) throw new Error(`${put.status} ${await put.text()}`);
        setMsg("Saved.");
        router.refresh();
      } catch (e) {
        setMsg(e instanceof Error ? `Save failed: ${e.message}` : "Save failed");
      }
    });
  }

  // Summary by layer type for the right rail
  const summary = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const f of fc.features) {
      const k = f.properties.layer_type + (f.properties.year ? ` · Year ${f.properties.year}` : "");
      counts[k] = (counts[k] ?? 0) + 1;
    }
    return Object.entries(counts).sort();
  }, [fc]);

  // savedActionRef tracks an explicit save button click — placeholder for future undo
  const savedActionRef = useRef(0);
  savedActionRef.current = fc.features.length;

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
          Raster underlay
        </div>
        {surfaceUpload ? (
          <>
            <div className="text-xs text-slate-600">
              Source: <span className="font-medium">{surfaceUpload.filename}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Label htmlFor="nwLat" className="text-[10px]">NW lat</Label>
              <Input id="nwLat" value={nw.lat} onChange={(e) => setNw((p) => ({ ...p, lat: e.target.value }))} className="h-7 w-20 px-2" placeholder="27.205" />
              <Label htmlFor="nwLng" className="text-[10px]">NW lng</Label>
              <Input id="nwLng" value={nw.lng} onChange={(e) => setNw((p) => ({ ...p, lng: e.target.value }))} className="h-7 w-20 px-2" placeholder="73.645" />
            </div>
            <div className="flex items-center gap-1.5">
              <Label htmlFor="seLat" className="text-[10px]">SE lat</Label>
              <Input id="seLat" value={se.lat} onChange={(e) => setSe((p) => ({ ...p, lat: e.target.value }))} className="h-7 w-20 px-2" placeholder="27.195" />
              <Label htmlFor="seLng" className="text-[10px]">SE lng</Label>
              <Input id="seLng" value={se.lng} onChange={(e) => setSe((p) => ({ ...p, lng: e.target.value }))} className="h-7 w-20 px-2" placeholder="73.660" />
            </div>
            <Button
              type="button"
              size="sm"
              variant={underlayActive ? "secondary" : "outline"}
              disabled={!underlayBounds}
              onClick={() => setUnderlayActive((a) => !a)}
            >
              {underlayActive ? "Hide" : "Show"} underlay
            </Button>
          </>
        ) : (
          <div className="text-xs text-slate-500">
            No surface plan uploaded yet — draw on the OpenStreetMap base or go back and upload one.
          </div>
        )}
      </div>

      <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-[1fr_260px]">
        <div className="min-h-[60vh] overflow-hidden rounded-lg">
          <LeafletEditor
            initial={fc}
            underlayUrl={underlayActive && surfaceUpload ? `/api/projects/${slug}/uploads/${surfaceUpload.id}` : null}
            underlayBounds={underlayActive ? underlayBounds : null}
            onChange={setFc}
            onLeaseSet={onLeaseSet}
          />
        </div>

        <aside className="space-y-3">
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Shield className="h-3.5 w-3.5" /> Layer summary
            </div>
            {summary.length === 0 ? (
              <p className="text-xs text-slate-500">Nothing drawn yet.</p>
            ) : (
              <ul className="space-y-1 text-xs text-slate-700">
                {summary.map(([k, n]) => {
                  const baseType = k.split(" · ")[0] as keyof typeof LAYER_LABELS;
                  const yearSuffix = k.includes(" · ") ? k.slice(k.indexOf(" · ")) : "";
                  return (
                    <li key={k} className="flex items-center justify-between">
                      <span>{LAYER_LABELS[baseType] ?? baseType}{yearSuffix}</span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium">{n}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <Button type="button" variant="primary" disabled={saving || busy} onClick={save} className="w-full">
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save layers"}
          </Button>

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
