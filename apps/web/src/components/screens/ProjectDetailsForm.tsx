"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FileText, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ProjectDetails, MiningPlanProject } from "@/lib/types";

const schema = z.object({
  project_name: z.string().min(2, "Project name is required"),
  applicant_name: z.string().optional().default(""),
  mineral: z.string().optional().default(""),
  village: z.string().optional().default(""),
  tehsil: z.string().optional().default(""),
  district: z.string().optional().default(""),
  state: z.string().optional().default(""),
  area_ha: z.coerce.number().positive("Area must be > 0"),
  map_type: z.string().default("year_wise_mining_plan"),
  scale: z.string().default("1:1000"),
  survey_date: z.string().optional().default(""),
  plan_period_years: z.coerce.number().int().min(1).max(5).default(5),
});

type FormValues = z.infer<typeof schema>;

const MAP_TYPES: { value: string; label: string }[] = [
  { value: "surface_plan", label: "Surface Plan" },
  { value: "surface_geological_plan", label: "Surface Geological Plan" },
  { value: "geological_plan", label: "Geological Plan" },
  { value: "geological_section", label: "Geological Section" },
  { value: "progressive_mine_closure_plan", label: "Progressive Mine Closure Plan" },
  { value: "conceptual_plan", label: "Conceptual Plan" },
  { value: "environment_plan", label: "Environment Plan" },
  { value: "key_plan", label: "Key Plan" },
  { value: "financial_assurance_plan", label: "Financial Assurance Plan" },
  { value: "year_wise_mining_plan", label: "Year-Wise Mining Plan" },
  { value: "other", label: "Other" },
];

const SAMPLE: FormValues = {
  project_name: "Haripura Limestone Block TKSB-18",
  applicant_name: "M/s. Example",
  mineral: "Limestone",
  village: "Haripura",
  tehsil: "Kheenvsar",
  district: "Nagaur",
  state: "Rajasthan",
  area_ha: 4.8,
  map_type: "year_wise_mining_plan",
  scale: "1:1000",
  survey_date: "2025-03-10",
  plan_period_years: 5,
};

interface Props {
  mode: "new" | "edit";
  slug?: string;
  initial?: ProjectDetails;
}

export function ProjectDetailsForm({ mode, slug, initial }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: (initial as FormValues | undefined) ?? {
      project_name: "",
      applicant_name: "",
      mineral: "",
      village: "",
      tehsil: "",
      district: "",
      state: "",
      area_ha: 0,
      map_type: "year_wise_mining_plan",
      scale: "1:1000",
      survey_date: "",
      plan_period_years: 5,
    },
  });

  const onSubmit = form.handleSubmit((values) => {
    setSubmitError(null);
    startTransition(async () => {
      try {
        const payload: MiningPlanProject = { project_details: values as ProjectDetails };
        if (mode === "new") {
          const res = await fetch("/api/projects", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
          const created = (await res.json()) as { slug: string };
          router.push(`/project/${created.slug}/2`);
          router.refresh();
        } else if (slug) {
          // Edit: preserve other slices via merging upstream.
          const cur = await (await fetch(`/api/projects/${slug}`)).json();
          const merged = { ...cur, project_details: values };
          const res = await fetch(`/api/projects/${slug}`, {
            method: "PUT",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(merged),
          });
          if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
          router.push(`/project/${slug}/2`);
          router.refresh();
        }
      } catch (e) {
        setSubmitError(e instanceof Error ? e.message : "Save failed");
      }
    });
  });

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <FileText className="h-4 w-4 text-amber-500" />
            Create New Mining Plan Project
          </div>
          {mode === "new" && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => form.reset(SAMPLE)}
            >
              <Wand2 className="h-3.5 w-3.5" />
              Load Sample Project
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Project Name *" error={form.formState.errors.project_name?.message}>
            <Input {...form.register("project_name")} placeholder="e.g. Haripura Limestone Block TKSB-18" />
          </Field>
          <Field label="Applicant Name">
            <Input {...form.register("applicant_name")} placeholder="M/s. Example" />
          </Field>
          <Field label="Mineral">
            <Input {...form.register("mineral")} placeholder="Limestone" />
          </Field>
          <Field label="Village">
            <Input {...form.register("village")} />
          </Field>
          <Field label="Tehsil">
            <Input {...form.register("tehsil")} />
          </Field>
          <Field label="District">
            <Input {...form.register("district")} />
          </Field>
          <Field label="State">
            <Input {...form.register("state")} placeholder="Rajasthan" />
          </Field>
          <Field label="Area (Hectare) *" error={form.formState.errors.area_ha?.message}>
            <Input type="number" step="0.001" {...form.register("area_ha")} />
          </Field>
          <Field label="Map Type">
            <select
              {...form.register("map_type")}
              className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              {MAP_TYPES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Scale">
            <select
              {...form.register("scale")}
              className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              {["1:500", "1:1000", "1:2000", "1:4000", "1:5000"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
          <Field label="Survey Date">
            <Input type="date" {...form.register("survey_date")} />
          </Field>
          <Field label="Plan Period (years)">
            <select
              {...form.register("plan_period_years")}
              className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              {[1, 2, 3, 4, 5].map((y) => (
                <option key={y} value={y}>{y} year{y > 1 ? "s" : ""}</option>
              ))}
            </select>
          </Field>
        </div>

        {submitError && (
          <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {submitError}
          </p>
        )}
      </div>

      <div className="flex items-center justify-end gap-3">
        <Button type="button" variant="outline" onClick={() => form.reset()} disabled={isPending}>
          Reset
        </Button>
        <Button type="submit" variant="primary" disabled={isPending}>
          {isPending ? "Saving…" : mode === "new" ? "Save & Continue" : "Save Changes"}
        </Button>
      </div>
    </form>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <Label className="mb-1">{label}</Label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}
