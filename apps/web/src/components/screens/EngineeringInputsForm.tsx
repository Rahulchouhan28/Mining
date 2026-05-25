"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { useForm, Controller, type Path } from "react-hook-form";
import { AlertTriangle, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { EngineeringInputs, MiningPlanProject } from "@/lib/types";

interface Props {
  slug: string;
  initial: EngineeringInputs;
}

const DEFAULTS: EngineeringInputs = {
  production: {
    annual_production_target_tonnes: 50000,
    approved_capacity_tonnes_per_year: 50000,
    working_days_per_year: 250,
    shifts_per_day: 1,
    hours_per_shift: 8,
  },
  bench: {
    bench_height_m: 6,
    bench_width_m: 6,
    face_slope_degree: 70,
    overall_pit_slope_degree: 45,
    ultimate_pit_depth_m: 42,
  },
  mineral_waste: {
    bulk_density_t_per_m3: 2.4,
    topsoil_thickness_m: 0.3,
    overburden_thickness_m: 1.0,
    mineral_recovery_percent: 90,
    reject_percent: 10,
  },
  machinery: {
    excavator_bucket_capacity_m3: 1.2,
    number_of_excavators: 1,
    dumper_capacity_tonnes: 16,
    number_of_dumpers: 3,
    crusher_capacity_tph: 100,
    drill_machine_available: true,
    blasting_required: true,
  },
  grade: { CaCO3: 92, CaO: 51.5, MgO: 1.2, SiO2: 3.5, Al2O3: 0.8, Fe2O3: 0.6, LOI: 41, Moisture: 1 },
  environmental_constraints: {
    water_body_distance_m: 450,
    village_distance_m: 600,
    sensitive_structure_distance_m: 1200,
    electric_line_present: false,
    drainage_present: true,
    forest_land_present: false,
    private_land_present: true,
    government_land_present: true,
  },
  assumed_fields: [],
};

export function EngineeringInputsForm({ slug, initial }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [err, setErr] = useState<string | null>(null);
  const [assumed, setAssumed] = useState<Set<string>>(new Set(initial.assumed_fields ?? []));

  const form = useForm<EngineeringInputs>({
    defaultValues: mergeDefaults(initial, DEFAULTS),
  });

  function applyDefaults() {
    form.reset(DEFAULTS);
    const allKeys = enumerateAllFieldPaths(DEFAULTS);
    setAssumed(new Set(allKeys));
  }

  const onSubmit = form.handleSubmit((values) => {
    startTransition(async () => {
      setErr(null);
      try {
        const cur = await (await fetch(`/api/projects/${slug}`)).json();
        const merged: MiningPlanProject = {
          ...cur,
          engineering_inputs: { ...values, assumed_fields: [...assumed] },
        };
        const r = await fetch(`/api/projects/${slug}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(merged),
        });
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        router.push(`/project/${slug}/5`);
        router.refresh();
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Save failed");
      }
    });
  });

  function NumberField({ name, label, step = 1 }: { name: Path<EngineeringInputs>; label: string; step?: number | string }) {
    return (
      <div>
        <Label className="mb-1 flex items-center gap-1">
          {label}
          {assumed.has(name) && (
            <span className="ml-1 inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-semibold text-amber-800">
              <AlertTriangle className="h-3 w-3" />
              ASSUMED
            </span>
          )}
        </Label>
        <Controller
          control={form.control}
          name={name}
          render={({ field }) => (
            <Input
              type="number"
              step={step}
              value={(field.value as number | undefined) ?? ""}
              onChange={(e) => field.onChange(e.target.value === "" ? undefined : Number(e.target.value))}
            />
          )}
        />
      </div>
    );
  }

  function CheckboxField({ name, label }: { name: Path<EngineeringInputs>; label: string }) {
    return (
      <label className="flex items-center gap-2 text-xs text-slate-700">
        <Controller
          control={form.control}
          name={name}
          render={({ field }) => (
            <input
              type="checkbox"
              checked={Boolean(field.value)}
              onChange={(e) => field.onChange(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-amber-500 focus:ring-amber-500"
            />
          )}
        />
        {label}
      </label>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5">
        <div className="text-xs text-amber-900">
          Unknown values? Load conceptual defaults — they will be tagged{" "}
          <span className="font-semibold">ASSUMED — NEEDS VALIDATION</span>.
        </div>
        <Button type="button" variant="outline" size="sm" onClick={applyDefaults}>
          <Wand2 className="h-3.5 w-3.5" />
          Use Conceptual Defaults
        </Button>
      </div>

      <Section title="A. Production">
        <NumberField name="production.annual_production_target_tonnes" label="Annual production target (t)" />
        <NumberField name="production.approved_capacity_tonnes_per_year" label="Approved capacity (t/y)" />
        <NumberField name="production.working_days_per_year" label="Working days / year" />
        <NumberField name="production.shifts_per_day" label="Shifts / day" />
        <NumberField name="production.hours_per_shift" label="Hours / shift" step={0.5} />
      </Section>

      <Section title="B. Bench Design">
        <NumberField name="bench.bench_height_m" label="Bench height (m)" step={0.1} />
        <NumberField name="bench.bench_width_m" label="Bench width (m)" step={0.1} />
        <NumberField name="bench.face_slope_degree" label="Face slope (°)" step={1} />
        <NumberField name="bench.overall_pit_slope_degree" label="Overall pit slope (°)" step={1} />
        <NumberField name="bench.ultimate_pit_depth_m" label="Ultimate pit depth (m)" step={1} />
      </Section>

      <Section title="C. Mineral & Waste">
        <NumberField name="mineral_waste.bulk_density_t_per_m3" label="Bulk density (t/m³)" step={0.01} />
        <NumberField name="mineral_waste.topsoil_thickness_m" label="Topsoil thickness (m)" step={0.05} />
        <NumberField name="mineral_waste.overburden_thickness_m" label="Overburden thickness (m)" step={0.1} />
        <NumberField name="mineral_waste.mineral_recovery_percent" label="Mineral recovery (%)" step={1} />
        <NumberField name="mineral_waste.reject_percent" label="Reject (%)" step={1} />
      </Section>

      <Section title="D. Machinery">
        <NumberField name="machinery.excavator_bucket_capacity_m3" label="Excavator bucket (m³)" step={0.1} />
        <NumberField name="machinery.number_of_excavators" label="# Excavators" />
        <NumberField name="machinery.dumper_capacity_tonnes" label="Dumper capacity (t)" />
        <NumberField name="machinery.number_of_dumpers" label="# Dumpers" />
        <NumberField name="machinery.crusher_capacity_tph" label="Crusher capacity (tph)" />
        <div className="col-span-2 flex flex-wrap gap-4 pt-2">
          <CheckboxField name="machinery.drill_machine_available" label="Drill machine available" />
          <CheckboxField name="machinery.blasting_required" label="Blasting required" />
        </div>
      </Section>

      <Section title="E. Grade / Chemical Analysis (%)">
        {Object.keys(DEFAULTS.grade ?? {}).map((k) => (
          <NumberField key={k} name={`grade.${k}` as Path<EngineeringInputs>} label={k} step={0.1} />
        ))}
      </Section>

      <Section title="F. Environmental Constraints">
        <NumberField name="environmental_constraints.water_body_distance_m" label="Water body distance (m)" />
        <NumberField name="environmental_constraints.village_distance_m" label="Village distance (m)" />
        <NumberField name="environmental_constraints.sensitive_structure_distance_m" label="Sensitive structure distance (m)" />
        <div className="col-span-2 flex flex-wrap gap-4 pt-2">
          <CheckboxField name="environmental_constraints.electric_line_present" label="Electric line present" />
          <CheckboxField name="environmental_constraints.drainage_present" label="Nala/drainage present" />
          <CheckboxField name="environmental_constraints.forest_land_present" label="Forest land present" />
          <CheckboxField name="environmental_constraints.private_land_present" label="Private land present" />
          <CheckboxField name="environmental_constraints.government_land_present" label="Government land present" />
        </div>
      </Section>

      {err && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {err}
        </p>
      )}

      <div className="flex justify-end gap-3">
        <Button type="submit" variant="primary" disabled={pending}>
          {pending ? "Saving…" : "Save & Continue"}
        </Button>
      </div>
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="rounded-lg border border-slate-200 bg-white p-5">
      <legend className="px-2 text-xs font-semibold uppercase tracking-wider text-amber-600">
        {title}
      </legend>
      <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">{children}</div>
    </fieldset>
  );
}

function mergeDefaults(initial: EngineeringInputs, defaults: EngineeringInputs): EngineeringInputs {
  // Shallow per-section merge; values in `initial` win.
  const out: EngineeringInputs = {};
  for (const k of Object.keys(defaults) as (keyof EngineeringInputs)[]) {
    const left = (initial as Record<string, unknown>)[k] as Record<string, unknown> | undefined;
    const right = (defaults as Record<string, unknown>)[k] as Record<string, unknown> | undefined;
    (out as Record<string, unknown>)[k] = left && typeof left === "object" ? { ...right, ...left } : (left ?? right);
  }
  return out;
}

function enumerateAllFieldPaths(o: EngineeringInputs, prefix = ""): string[] {
  const out: string[] = [];
  for (const [k, v] of Object.entries(o)) {
    const p = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      out.push(...enumerateAllFieldPaths(v as EngineeringInputs, p));
    } else if (typeof v === "number" || typeof v === "boolean") {
      out.push(p);
    }
  }
  return out;
}
