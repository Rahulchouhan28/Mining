import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { STEPS, type StepNumber } from "@/lib/types";

interface Props {
  slug: string;
  step: StepNumber;
  title: string;
  description?: string;
  children: React.ReactNode;
  /**
   * Optional override for the primary action. If provided, replaces the default
   * "Save & Continue" link with custom content (button form-submit, etc.).
   */
  primaryAction?: React.ReactNode;
}

export function StepShell({ slug, step, title, description, children, primaryAction }: Props) {
  const meta = STEPS.find((s) => s.num === step)!;
  const prev = step > 1 ? step - 1 : null;
  const next = step < 9 ? step + 1 : null;

  return (
    <div className="flex h-full flex-1 flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-8 py-5">
        <div className="text-xs font-medium uppercase tracking-wider text-amber-600">
          Step {meta.num} of 9
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
      </header>

      <main className="flex-1 overflow-y-auto px-8 py-6">{children}</main>

      <footer className="flex items-center justify-between border-t border-slate-200 bg-white px-8 py-4">
        {prev ? (
          <Link href={`/project/${slug}/${prev}`}>
            <Button variant="outline" size="md">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </Link>
        ) : (
          <span />
        )}

        {primaryAction ??
          (next ? (
            <Link href={`/project/${slug}/${next}`}>
              <Button variant="primary" size="md">
                Continue
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          ) : null)}
      </footer>
    </div>
  );
}
