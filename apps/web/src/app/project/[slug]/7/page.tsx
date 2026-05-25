import { StepShell } from "@/components/stepper/StepShell";
import { ReviewScreen } from "@/components/review/ReviewScreen";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step7Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={7}
      title="Review Generated Mining Plan"
      description="Inspect, toggle layers, switch alternatives. Tick the approval checkbox before exporting the PDF."
      primaryAction={null}
    >
      <ReviewScreen slug={slug} project={project} />
    </StepShell>
  );
}
