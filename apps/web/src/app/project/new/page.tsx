import Link from "next/link";
import { ArrowLeft, MapPin } from "lucide-react";
import { ProjectDetailsForm } from "@/components/screens/ProjectDetailsForm";

export default function NewProjectPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <MapPin className="h-6 w-6 text-amber-400" />
            <div>
              <h1 className="text-lg font-semibold tracking-tight">New Mining Plan Project</h1>
              <p className="text-xs text-slate-400">Step 1 of 9 — Project Setup</p>
            </div>
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to projects
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-8">
        <ProjectDetailsForm mode="new" />
      </section>
    </div>
  );
}
