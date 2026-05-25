import { notFound } from "next/navigation";
import { getProject } from "@/lib/api";
import { StepperSidebar } from "@/components/stepper/StepperSidebar";

interface Props {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}

export default async function ProjectLayout({ children, params }: Props) {
  const { slug } = await params;
  let project;
  try {
    project = await getProject(slug);
  } catch {
    notFound();
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-50">
      <StepperSidebar slug={slug} projectName={project.project_details.project_name} />
      {children}
    </div>
  );
}
