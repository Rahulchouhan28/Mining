import { StepShell } from "@/components/stepper/StepShell";
import { DigitizeScreen } from "@/components/digitize/DigitizeScreen";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step3Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);

  return (
    <StepShell
      slug={slug}
      step={3}
      title="Digitize Map Layers"
      description="Draw the lease boundary first — the 7.5 m statutory barrier auto-generates. Then add year-wise pits, dumps, plantation, and infrastructure."
    >
      <DigitizeScreen slug={slug} project={project} />
    </StepShell>
  );
}
