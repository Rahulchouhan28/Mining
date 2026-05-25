import { getProject } from "@/lib/api";
import { ProjectDetailsForm } from "@/components/screens/ProjectDetailsForm";
import { StepShell } from "@/components/stepper/StepShell";

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function Step1Page({ params }: Props) {
  const { slug } = await params;
  const project = await getProject(slug);

  return (
    <StepShell
      slug={slug}
      step={1}
      title="Project Setup"
      description="Edit basic project details. Saving will advance to the upload step."
      primaryAction={null}
    >
      <ProjectDetailsForm mode="edit" slug={slug} initial={project.project_details} />
    </StepShell>
  );
}
