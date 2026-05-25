"use client";

import { useState, useTransition } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { Alternative, MiningPlanProject } from "@/lib/types";

interface Props {
  slug: string;
  project: MiningPlanProject;
}

export function PdfComposerScreen({ slug, project }: Props) {
  const alternatives = project.selected_alternatives ?? ["base"];
  const [alt, setAlt] = useState<Alternative>(alternatives[0] ?? "base");
  const [plate, setPlate] = useState("year_wise_mining_plan");
  const [paper, setPaper] = useState("A3");
  const [orientation, setOrientation] = useState("landscape");
  const [scale, setScale] = useState(1000);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pending, startPending] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function compose() {
    startPending(async () => {
      setError(null);
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
      const params = new URLSearchParams({
        alternative: alt,
        plate_type: plate,
        paper,
        orientation,
        scale: String(scale),
      });
      try {
        const r = await fetch(`/api/projects/${slug}/export/pdf?${params}`);
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        const blob = await r.blob();
        setPdfBlobUrl(URL.createObjectURL(blob));
      } catch (e) {
        setError(e instanceof Error ? e.message : "PDF generation failed");
      }
    });
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 rounded-lg border border-slate-200 bg-white p-5 lg:grid-cols-5">
        <div>
          <Label className="mb-1">Alternative</Label>
          <select className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm"
                  value={alt} onChange={(e) => setAlt(e.target.value as Alternative)}>
            {alternatives.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div>
          <Label className="mb-1">Plate type</Label>
          <select className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm"
                  value={plate} onChange={(e) => setPlate(e.target.value)}>
            <option value="year_wise_mining_plan">Year-Wise Mining Plan</option>
            <option value="progressive_mine_closure_plan">Progressive Mine Closure Plan</option>
            <option value="conceptual_plan">Conceptual Plan</option>
            <option value="environment_plan">Environment Plan</option>
          </select>
        </div>
        <div>
          <Label className="mb-1">Paper</Label>
          <select className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm"
                  value={paper} onChange={(e) => setPaper(e.target.value)}>
            <option value="A4">A4</option>
            <option value="A3">A3</option>
            <option value="A2">A2</option>
          </select>
        </div>
        <div>
          <Label className="mb-1">Orientation</Label>
          <select className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm"
                  value={orientation} onChange={(e) => setOrientation(e.target.value)}>
            <option value="landscape">Landscape</option>
            <option value="portrait">Portrait</option>
          </select>
        </div>
        <div>
          <Label className="mb-1">Scale 1 :</Label>
          <select className="h-9 w-full rounded-md border border-slate-300 px-2 text-sm"
                  value={scale} onChange={(e) => setScale(Number(e.target.value))}>
            {[500, 1000, 2000, 4000, 5000].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
        <div className="text-xs text-slate-600">
          Plates are vector PDFs rendered at the requested scale via Cartopy + Matplotlib in UTM 43 N.
        </div>
        <Button type="button" variant="primary" disabled={pending} onClick={compose}>
          {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
          {pending ? "Composing…" : "Generate PDF"}
        </Button>
      </div>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}

      {pdfBlobUrl && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-700">Preview</h3>
            <a
              href={pdfBlobUrl}
              download={`${slug}_${plate}_${alt}_1to${scale}.pdf`}
              className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-slate-800"
            >
              <Download className="h-3.5 w-3.5" />
              Download
            </a>
          </div>
          <iframe src={pdfBlobUrl} className="h-[70vh] w-full rounded border border-slate-200" />
        </div>
      )}
    </div>
  );
}
