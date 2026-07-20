"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileUp, Image as ImageIcon, FileText, FileSpreadsheet, Trash2, Loader2, Eye, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { renderPageToDataUrl, getPageCount } from "@/lib/pdf";
import type { UploadedFile, UploadCategory } from "@/lib/types";

type Thumb = { page: number; dataUrl: string };

interface CardSpec {
  category: UploadCategory;
  title: string;
  accepted: string;
  accept: string;
}

const CARDS: CardSpec[] = [
  { category: "approved_mining_plan",          title: "Approved Mining Plan",         accepted: "PDF",                               accept: ".pdf" },
  { category: "surface_plan",                  title: "Surface Plan",                 accepted: "PDF, KML, KMZ, GeoJSON, JPG, PNG",  accept: ".pdf,.kml,.kmz,.geojson,.json,.jpg,.jpeg,.png" },
  { category: "geological_plan",               title: "Geological Plan",              accepted: "PDF, KML, KMZ, GeoJSON, image",     accept: ".pdf,.kml,.kmz,.geojson,.json,.jpg,.jpeg,.png" },
  { category: "geological_section",            title: "Geological Section",           accepted: "PDF, image",                        accept: ".pdf,.jpg,.jpeg,.png" },
  { category: "environment_plan",              title: "Environment Plan",             accepted: "PDF, KML, KMZ, image",              accept: ".pdf,.kml,.kmz,.jpg,.jpeg,.png" },
  { category: "key_plan",                      title: "Key Plan",                     accepted: "PDF, image",                        accept: ".pdf,.jpg,.jpeg,.png" },
  { category: "progressive_mine_closure_plan", title: "Progressive Mine Closure Plan",accepted: "PDF, KML, KMZ, image",              accept: ".pdf,.kml,.kmz,.jpg,.jpeg,.png" },
  { category: "conceptual_plan",               title: "Conceptual Plan",              accepted: "PDF, KML, KMZ, image",              accept: ".pdf,.kml,.kmz,.jpg,.jpeg,.png" },
  { category: "financial_assurance_plan",      title: "Financial Assurance Plan",     accepted: "PDF, KML, KMZ, Excel, image",       accept: ".pdf,.kml,.kmz,.xlsx,.xls,.jpg,.jpeg,.png" },
  { category: "proposed_five_year_development_plan", title: "Five Year Development Plan", accepted: "PDF, KML, KMZ",                     accept: ".pdf,.kml,.kmz" },
  { category: "year_1_plan",                   title: "Year 1 Plan",                  accepted: "PDF, KML, KMZ",                     accept: ".pdf,.kml,.kmz" },
  { category: "year_2_plan",                   title: "Year 2 Plan",                  accepted: "PDF, KML, KMZ",                     accept: ".pdf,.kml,.kmz" },
  { category: "year_3_plan",                   title: "Year 3 Plan",                  accepted: "PDF, KML, KMZ",                     accept: ".pdf,.kml,.kmz" },
  { category: "year_4_plan",                   title: "Year 4 Plan",                  accepted: "PDF, KML, KMZ",                     accept: ".pdf,.kml,.kmz" },
  { category: "year_5_plan",                   title: "Year 5 Plan",                  accepted: "PDF, KML, KMZ",                     accept: ".pdf,.kml,.kmz" },
  { category: "borehole_data",                 title: "Borehole Data",                accepted: "Excel, CSV, PDF",                   accept: ".xlsx,.xls,.csv,.pdf" },
  { category: "chemical_analysis",             title: "Chemical Analysis",            accepted: "Excel, CSV, PDF",                   accept: ".xlsx,.xls,.csv,.pdf" },
  { category: "production_data",               title: "Production Data",              accepted: "Excel, CSV, PDF",                   accept: ".xlsx,.xls,.csv,.pdf" },
  { category: "annexures",                     title: "Annexures & Others",           accepted: "PDF, Excel, Word, image",           accept: ".pdf,.xlsx,.xls,.doc,.docx,.jpg,.jpeg,.png" },
];

interface Props {
  slug: string;
  initialFiles: UploadedFile[];
}

export function UploadScreen({ slug, initialFiles }: Props) {
  const router = useRouter();
  const [files, setFiles] = useState<UploadedFile[]>(initialFiles);
  const [uploadingCat, setUploadingCat] = useState<UploadCategory | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filesByCategory = files.reduce<Record<string, UploadedFile[]>>((acc, f) => {
    (acc[f.category] ??= []).push(f);
    return acc;
  }, {});

  const onUpload = useCallback(
    async (file: File, category: UploadCategory) => {
      setError(null);
      setUploadingCat(category);
      try {
        const fd = new FormData();
        fd.append("category", category);
        fd.append("file", file);
        const res = await fetch(`/api/projects/${slug}/uploads`, { method: "POST", body: fd });
        if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
        const record = (await res.json()) as UploadedFile;
        setFiles((prev) => [...prev, record]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploadingCat(null);
      }
    },
    [slug],
  );


  const totalCount = files.length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((c) => (
          <UploadCard
            key={c.category}
            spec={c}
            files={filesByCategory[c.category] ?? []}
            onUpload={(f) => onUpload(f, c.category)}
            slug={slug}
            uploading={uploadingCat === c.category}
            onDelete={(id) => setFiles((prev) => prev.filter((x) => x.id !== id))}
          />
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      <div className="sticky bottom-0 z-10 -mx-8 border-t border-slate-200 bg-white px-8 py-4 shadow-lg">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div className="text-xs text-slate-600">
            <span className="font-medium text-slate-900">{totalCount}</span> file{totalCount === 1 ? "" : "s"} uploaded
          </div>
        </div>
      </div>

      <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
        Upload as many files as you have. These files will be stored in your project's document repository.
      </p>
    </div>
  );
}

function UploadCard({
  spec,
  files,
  onUpload,
  slug,
  uploading,
  onDelete,
}: {
  spec: CardSpec;
  files: UploadedFile[];
  onUpload: (f: File) => void;
  slug: string;
  uploading: boolean;
  onDelete: (id: string) => void;
}) {
  const [over, setOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [openPreview, setOpenPreview] = useState<string | null>(null);

  const hasFiles = files.length > 0;

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onUpload(f);
        }}
        className={cn(
          "rounded-t-lg border-b p-4 transition-colors",
          over ? "border-amber-400 bg-amber-50" : hasFiles ? "border-emerald-200 bg-emerald-50/40" : "border-slate-200 bg-slate-50",
          uploading && "opacity-60",
        )}
      >
        <div className="flex items-start gap-2">
          <FileUp className={cn("h-5 w-5 shrink-0", hasFiles ? "text-emerald-500" : "text-amber-500")} />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-slate-900">{spec.title}</h3>
            <p className="text-[11px] text-slate-500">{spec.accepted}</p>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={spec.accept}
          className="hidden"
          disabled={uploading}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = "";
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-3 w-full"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Choose file"}
        </Button>
      </div>
      {hasFiles && (
        <ul className="divide-y divide-slate-100 text-xs">
          {files.map((f) => (
            <li key={f.id}>
              <UploadedRow
                slug={slug}
                file={f}
                open={openPreview === f.id}
                onToggle={() => setOpenPreview(openPreview === f.id ? null : f.id)}
                onDelete={() => onDelete(f.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function UploadedRow({
  slug, file, open, onToggle, onDelete,
}: { slug: string; file: UploadedFile; open: boolean; onToggle: () => void; onDelete: () => void }) {
  const [thumbs, setThumbs] = useState<Thumb[]>([]);
  const [pageCount, setPageCount] = useState<number | null>(file.pages ?? null);
  const [loading, setLoading] = useState(false);
  const isPdf = file.mime_type === "application/pdf" || file.filename.toLowerCase().endsWith(".pdf");
  const isImage = file.mime_type?.startsWith("image/") || /\.(jpe?g|png|tiff?)$/i.test(file.filename);
  const isVector = /\.(kml|kmz|geojson|json)$/i.test(file.filename);
  const isData = /\.(csv|xlsx|xls)$/i.test(file.filename);

  useEffect(() => {
    if (!open || !isPdf || thumbs.length > 0) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const blob = await (await fetch(`/api/projects/${slug}/uploads/${file.id}`)).blob();
        const pc = await getPageCount(blob);
        if (cancelled) return;
        setPageCount(pc);
        const limit = Math.min(pc, 8);
        const out: Thumb[] = [];
        for (let i = 1; i <= limit; i++) {
          const { dataUrl } = await renderPageToDataUrl(blob, i, 200);
          if (cancelled) return;
          out.push({ page: i, dataUrl });
          setThumbs([...out]);
        }
      } catch (e) {
        console.error(e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open, isPdf, slug, file.id, thumbs.length]);

  const icon = isPdf ? <FileText className="h-4 w-4 text-rose-500" />
            : isImage ? <ImageIcon className="h-4 w-4 text-emerald-500" />
            : isData ? <FileSpreadsheet className="h-4 w-4 text-green-600" />
            : isVector ? <FileText className="h-4 w-4 text-sky-500" />
            : <FileText className="h-4 w-4 text-slate-400" />;

  return (
    <>
      <div className="flex items-center gap-2 px-3 py-2">
        {icon}
        <div className="flex-1 min-w-0">
          <div className="truncate text-[12px] font-medium text-slate-800">{file.filename}</div>
          <div className="text-[10px] text-slate-500">
            {file.size_bytes ? `${(file.size_bytes / 1024).toFixed(1)} KB` : ""}
            {pageCount ? ` · ${pageCount} pages` : ""}
            {isVector && " · vector"}
          </div>
        </div>
        {(isPdf || isImage) && (
          <button type="button" onClick={onToggle} className="text-slate-500 hover:text-amber-600">
            <Eye className="h-4 w-4" />
          </button>
        )}
        <button type="button" onClick={onDelete} className="text-slate-400 hover:text-red-500">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {open && (
        <div className="bg-slate-50 px-3 py-2">
          {isImage && (
            <img
              src={`/api/projects/${slug}/uploads/${file.id}`}
              alt={file.filename}
              className="mx-auto max-h-64 rounded shadow"
            />
          )}
          {isPdf && (
            <>
              {loading && (
                <div className="flex items-center gap-1 text-[10px] text-slate-500">
                  <Loader2 className="h-3 w-3 animate-spin" /> Rendering…
                </div>
              )}
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {thumbs.map((t) => (
                  <div key={t.page} className="overflow-hidden rounded border border-slate-200 bg-white">
                    <img src={t.dataUrl} alt={`Page ${t.page}`} className="block w-full" />
                    <div className="px-1.5 py-0.5 text-[9px] text-slate-500">Pg {t.page}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
