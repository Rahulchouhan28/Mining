import { StepShell } from "@/components/stepper/StepShell";
import { PdfComposerScreen } from "@/components/pdf/PdfComposerScreen";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step8Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={8}
      title="PDF Map Composer"
      description="Compose the final A3 statutory-style PDF sheet with title block, north arrow, scale bar, legend, and certification box."
    >
      <PdfComposerScreen slug={slug} project={project} />
    </StepShell>
  );
}
