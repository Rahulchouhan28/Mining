"use client";

import type * as PdfJs from "pdfjs-dist";

// Lazy-load pdfjs to keep it out of the main bundle and out of the server build.
// Worker is loaded from jsDelivr to match the installed package version.
let _pdfjs: typeof PdfJs | null = null;

const PDFJS_VERSION = "5.7.284";

export async function loadPdfJs(): Promise<typeof PdfJs> {
  if (_pdfjs) return _pdfjs;
  const mod = await import("pdfjs-dist");
  mod.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}/build/pdf.worker.min.mjs`;
  _pdfjs = mod;
  return mod;
}

export async function renderPageToDataUrl(
  file: File | Blob | ArrayBuffer,
  pageNumber: number,
  targetWidth: number,
): Promise<{ dataUrl: string; width: number; height: number }> {
  const pdfjs = await loadPdfJs();
  const data = file instanceof ArrayBuffer ? new Uint8Array(file) : new Uint8Array(await (file as Blob).arrayBuffer());
  const pdf = await pdfjs.getDocument({ data }).promise;
  const page = await pdf.getPage(pageNumber);
  const baseViewport = page.getViewport({ scale: 1 });
  const scale = targetWidth / baseViewport.width;
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not get canvas 2D context");
  await page.render({ canvasContext: ctx, viewport, canvas }).promise;
  return {
    dataUrl: canvas.toDataURL("image/png"),
    width: canvas.width,
    height: canvas.height,
  };
}

export async function getPageCount(file: File | Blob): Promise<number> {
  const pdfjs = await loadPdfJs();
  const data = new Uint8Array(await file.arrayBuffer());
  const pdf = await pdfjs.getDocument({ data }).promise;
  return pdf.numPages;
}
