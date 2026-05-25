import { StepShell } from "@/components/stepper/StepShell";
import { AutoPlanScreen } from "@/components/screens/AutoPlanScreen";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step6Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={6}
      title="Year-Wise Plan"
      description="Map below shows the auto-generated plan. Switch the approach to compare alternatives, tweak parameters in the edit block, and use the bottom-right button to download the PDF plate."
      primaryAction={null}
    >
      <AutoPlanScreen slug={slug} project={project} />
    </StepShell>
  );
}
