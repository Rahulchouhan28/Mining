import { StepShell } from "@/components/stepper/StepShell";
import { AlternativesForm } from "@/components/screens/AlternativesForm";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step5Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={5}
      title="Choose Planning Alternatives"
      description="Pick the alternatives the planner should generate. Base / Conservative / Aggressive ship in v1."
      primaryAction={null}
    >
      <AlternativesForm slug={slug} initial={project.selected_alternatives ?? ["base", "conservative", "aggressive"]} />
    </StepShell>
  );
}
