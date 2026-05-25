import { StepShell } from "@/components/stepper/StepShell";
import { EngineeringInputsForm } from "@/components/screens/EngineeringInputsForm";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step4Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={4}
      title="Engineering Inputs"
      description="Production, bench geometry, mineral / waste data, machinery, grade analysis and environmental constraints."
      primaryAction={null}
    >
      <EngineeringInputsForm slug={slug} initial={project.engineering_inputs ?? {}} />
    </StepShell>
  );
}
