"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Check, MapPin } from "lucide-react";
import { STEPS, type StepDef } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  slug: string;
  projectName: string;
}

function renderStep(s: StepDef, slug: string, currentStep: number) {
  const active = currentStep === s.num;
  const done = currentStep > s.num;
  return (
    <li key={s.num}>
      <Link
        href={`/project/${slug}/${s.num}`}
        className={cn(
          "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
          active && "bg-amber-500 text-slate-950 font-medium",
          !active && "text-slate-300 hover:bg-slate-800",
        )}
      >
        <span
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
            active && "bg-slate-950 text-amber-400",
            done && !active && "bg-emerald-500 text-white",
            !active && !done && "bg-slate-700 text-slate-300 group-hover:bg-slate-600",
          )}
        >
          {done && !active ? <Check className="h-3.5 w-3.5" /> : s.num}
        </span>
        <span className="truncate">{s.label}</span>
      </Link>
    </li>
  );
}

export function StepperSidebar({ slug, projectName }: Props) {
  const pathname = usePathname();
  const currentStep = parseInt(pathname.split("/").pop() ?? "1", 10);

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-900 text-slate-100">
      <Link href="/" className="border-b border-slate-800 px-5 py-4">
        <div className="flex items-center gap-2">
          <MapPin className="h-5 w-5 text-amber-400" />
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Mining Plan Generator
            </div>
            <div className="mt-0.5 truncate text-sm font-medium" title={projectName}>
              {projectName}
            </div>
          </div>
        </div>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Happy path
        </div>
        <ol className="space-y-1">
          {STEPS.filter((s) => !s.advanced).map((s) => renderStep(s, slug, currentStep))}
        </ol>
        <div className="mb-2 mt-5 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Advanced
        </div>
        <ol className="space-y-1">
          {STEPS.filter((s) => s.advanced).map((s) => renderStep(s, slug, currentStep))}
        </ol>
      </nav>

      <div className="border-t border-slate-800 px-4 py-3 text-[10px] leading-relaxed text-slate-500">
        Conceptual output. Final statutory submission must be signed by an RQP.
      </div>
    </aside>
  );
}
