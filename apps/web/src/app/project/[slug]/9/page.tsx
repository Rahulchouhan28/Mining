import { StepShell } from "@/components/stepper/StepShell";
import { ExportCenter } from "@/components/export/ExportCenter";
import { getProject } from "@/lib/api";

interface Props { params: Promise<{ slug: string }>; }

export default async function Step9Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);
  return (
    <StepShell
      slug={slug}
      step={9}
      title="Export Generated Plan"
      description="Download PDF plates, GeoJSON, KML, Excel quantity tables, or the full ZIP package."
      primaryAction={null}
    >
      <ExportCenter slug={slug} alternatives={project.selected_alternatives ?? ["base"]} />
    </StepShell>
  );
}
