import { redirect } from "next/navigation";

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function ProjectIndex({ params }: Props) {
  const { slug } = await params;
  redirect(`/project/${slug}/1`);
}
