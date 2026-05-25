import { StepShell } from "@/components/stepper/StepShell";
import { UploadScreen } from "@/components/upload/UploadScreen";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step2Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={2}
      title="Upload Mining Plans"
      description="Upload any of the 11 plan / data categories. KML, KMZ and GeoJSON files have their lease polygon parsed automatically; PDFs and images use the area from step 1 to draw a default lease that you can edit later."
      primaryAction={null}
    >
      <UploadScreen slug={slug} initialFiles={project.uploaded_files ?? []} />
    </StepShell>
  );
}
