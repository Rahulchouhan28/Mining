"use client";

import "leaflet/dist/leaflet.css";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "@geoman-io/leaflet-geoman-free";

import { LAYER_STYLES, LAYER_LABELS } from "./LayerCatalog";
import type { FeatureCollection, LayerFeature, LayerType } from "@/lib/types";

type DrawSpec = { layer_type: LayerType; year?: number };

interface Props {
  initial: FeatureCollection | null;
  underlayUrl?: string | null;
  underlayBounds?: [[number, number], [number, number]] | null;
  onChange: (fc: FeatureCollection) => void;
  /** Lease polygon callback so the parent can request the 7.5m barrier. */
  onLeaseSet?: (poly: GeoJSON.Polygon) => void;
}

const DEFAULT_CENTER: [number, number] = [27.2, 73.65]; // near Haripura
const DEFAULT_ZOOM = 16;

export default function LeafletEditor({
  initial,
  underlayUrl,
  underlayBounds,
  onChange,
  onLeaseSet,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.FeatureGroup | null>(null);
  const underlayRef = useRef<L.ImageOverlay | null>(null);
  const drawSpecRef = useRef<DrawSpec | null>(null);
  const [activeTool, setActiveTool] = useState<DrawSpec | null>(null);

  // boot map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      preferCanvas: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    const group = L.featureGroup().addTo(map);
    layerGroupRef.current = group;
    mapRef.current = map;

    // Geoman global options
    map.pm.setGlobalOptions({
      snappable: true,
      snapDistance: 12,
      allowSelfIntersection: false,
    });

    map.on("pm:create", (e: { layer: L.Layer }) => {
      const drawn = e.layer as L.Polygon | L.Polyline | L.Marker;
      const spec = drawSpecRef.current;
      if (!spec) {
        map.removeLayer(drawn);
        return;
      }
      const styling = LAYER_STYLES[spec.layer_type];
      const labelBits = [LAYER_LABELS[spec.layer_type]];
      if (spec.year) labelBits.push(`Year ${spec.year}`);
      if ("setStyle" in drawn) (drawn as L.Path).setStyle(styling);
      (drawn as L.Layer & { feature?: { properties: Record<string, unknown> } }).feature = {
        type: "Feature",
        properties: { layer_type: spec.layer_type, year: spec.year, label: labelBits.join(" "), color: styling.color },
        geometry: (drawn as unknown as { toGeoJSON: () => GeoJSON.Feature }).toGeoJSON().geometry,
      } as never;
      group.addLayer(drawn);
      drawn.bindTooltip(labelBits.join(" "), { permanent: false, direction: "center" });

      pushChange();

      if (spec.layer_type === "lease_boundary") {
        const gj = (drawn as unknown as { toGeoJSON: () => GeoJSON.Feature<GeoJSON.Polygon> }).toGeoJSON();
        onLeaseSet?.(gj.geometry);
      }

      // disable draw mode after one shape
      map.pm.disableDraw();
      drawSpecRef.current = null;
      setActiveTool(null);
    });

    map.on("pm:remove", () => pushChange());
    map.on("pm:edit", () => pushChange());

    function pushChange() {
      const features: LayerFeature[] = [];
      group.eachLayer((l) => {
        const feat = (l as L.Layer & { feature?: GeoJSON.Feature }).feature;
        if (!feat) return;
        const gj = (l as unknown as { toGeoJSON: () => GeoJSON.Feature }).toGeoJSON();
        features.push({
          type: "Feature",
          geometry: gj.geometry,
          properties: feat.properties as LayerFeature["properties"],
        });
      });
      onChange({ type: "FeatureCollection", features });
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // load initial features
  useEffect(() => {
    const map = mapRef.current;
    const group = layerGroupRef.current;
    if (!map || !group || !initial) return;
    group.clearLayers();
    for (const f of initial.features ?? []) {
      const styling = LAYER_STYLES[f.properties.layer_type];
      const gj = L.geoJSON(f, { style: styling as L.PathOptions });
      gj.eachLayer((sub) => {
        (sub as L.Layer & { feature?: GeoJSON.Feature }).feature = f as GeoJSON.Feature;
        const labelBits = [LAYER_LABELS[f.properties.layer_type]];
        if (f.properties.year) labelBits.push(`Year ${f.properties.year}`);
        sub.bindTooltip(labelBits.join(" "), { permanent: false, direction: "center" });
        if (f.properties.layer_type !== "statutory_barrier_7_5m") {
          // barrier is read-only / auto-generated
          group.addLayer(sub);
        } else {
          map.addLayer(sub);
        }
      });
    }
    try {
      const b = group.getBounds();
      if (b.isValid()) map.fitBounds(b, { padding: [20, 20] });
    } catch { /* empty */ }
  }, [initial]);

  // underlay image
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (underlayRef.current) {
      map.removeLayer(underlayRef.current);
      underlayRef.current = null;
    }
    if (underlayUrl && underlayBounds) {
      const overlay = L.imageOverlay(underlayUrl, underlayBounds, { opacity: 0.65 }).addTo(map);
      underlayRef.current = overlay;
      map.fitBounds(underlayBounds, { padding: [20, 20] });
    }
  }, [underlayUrl, underlayBounds]);

  function startDraw(spec: DrawSpec, shape: "Polygon" | "Line" | "Marker") {
    const map = mapRef.current;
    if (!map) return;
    drawSpecRef.current = spec;
    setActiveTool(spec);
    map.pm.disableDraw();
    map.pm.enableDraw(shape, { snappable: true, finishOn: "dblclick" });
  }

  function clearAll() {
    const group = layerGroupRef.current;
    if (!group) return;
    if (!confirm("Delete all drawn layers?")) return;
    group.clearLayers();
    onChange({ type: "FeatureCollection", features: [] });
  }

  function fitToLayers() {
    const group = layerGroupRef.current;
    const map = mapRef.current;
    if (!group || !map) return;
    try {
      const b = group.getBounds();
      if (b.isValid()) map.fitBounds(b, { padding: [20, 20] });
    } catch { /* empty */ }
  }

  const TOOLS: { spec: DrawSpec; shape: "Polygon" | "Line"; label: string; group: string }[] = [
    { spec: { layer_type: "lease_boundary" }, shape: "Polygon", label: "Lease Boundary", group: "Boundaries" },
    { spec: { layer_type: "ultimate_pit_limit" }, shape: "Polygon", label: "Ultimate Pit Limit", group: "Pits" },
    ...[1, 2, 3, 4, 5].map((y) => ({
      spec: { layer_type: "year_pit" as LayerType, year: y },
      shape: "Polygon" as const, label: `Year ${y} Pit`, group: "Pits",
    })),
    { spec: { layer_type: "overburden_dump" }, shape: "Polygon", label: "Overburden Dump", group: "Waste" },
    { spec: { layer_type: "topsoil_stack" }, shape: "Polygon", label: "Topsoil Stack", group: "Waste" },
    { spec: { layer_type: "backfill" }, shape: "Polygon", label: "Backfill Area", group: "Waste" },
    { spec: { layer_type: "plantation" }, shape: "Polygon", label: "Plantation", group: "Restoration" },
    { spec: { layer_type: "haul_road" }, shape: "Line", label: "Haul Road", group: "Infra" },
    { spec: { layer_type: "garland_drain" }, shape: "Line", label: "Garland Drain", group: "Infra" },
    { spec: { layer_type: "settling_tank" }, shape: "Polygon", label: "Settling Tank", group: "Infra" },
  ];

  const grouped: Record<string, typeof TOOLS> = {};
  for (const t of TOOLS) (grouped[t.group] ??= []).push(t);

  return (
    <div className="flex h-full w-full overflow-hidden rounded-lg border border-slate-200 bg-white">
      <aside className="w-60 shrink-0 overflow-y-auto border-r border-slate-200 bg-slate-50 px-3 py-3">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Draw Layer
        </div>
        {Object.entries(grouped).map(([gname, items]) => (
          <div key={gname} className="mb-4">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{gname}</div>
            <div className="space-y-1">
              {items.map((t) => {
                const active = activeTool && activeTool.layer_type === t.spec.layer_type && activeTool.year === t.spec.year;
                const style = LAYER_STYLES[t.spec.layer_type];
                return (
                  <button
                    key={t.label}
                    type="button"
                    onClick={() => startDraw(t.spec, t.shape)}
                    className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${
                      active ? "bg-amber-500 text-slate-950 font-medium" : "text-slate-700 hover:bg-white"
                    }`}
                  >
                    <span
                      className="inline-block h-3 w-3 shrink-0 rounded-sm border"
                      style={{ background: style.fillColor, borderColor: style.color }}
                    />
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <div className="mt-4 space-y-1 border-t border-slate-200 pt-3">
          <button
            type="button"
            onClick={fitToLayers}
            className="w-full rounded px-2 py-1.5 text-left text-xs text-slate-700 hover:bg-white"
          >
            Fit to drawn layers
          </button>
          <button
            type="button"
            onClick={clearAll}
            className="w-full rounded px-2 py-1.5 text-left text-xs text-red-600 hover:bg-red-50"
          >
            Clear all
          </button>
        </div>
        {activeTool && (
          <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-900">
            Click on the map to add vertices. Double-click to finish.
          </div>
        )}
      </aside>
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}
