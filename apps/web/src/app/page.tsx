import Link from "next/link";
import { FilePlus, FolderOpen, MapPin } from "lucide-react";

type ProjectListItem = {
  slug: string;
  project_name: string;
  updated_at?: string;
};

async function fetchProjects(): Promise<ProjectListItem[]> {
  try {
    const res = await fetch(`${process.env.FASTAPI_ORIGIN ?? "http://127.0.0.1:8000"}/api/projects`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return (await res.json()) as ProjectListItem[];
  } catch {
    return [];
  }
}

export default async function Home() {
  const projects = await fetchProjects();
  return (
    <main className="flex-1 bg-slate-50 dark:bg-slate-950">
      <header className="border-b border-slate-200 bg-slate-900 text-white dark:border-slate-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <MapPin className="h-6 w-6 text-amber-400" />
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Mining Plan Generator</h1>
              <p className="text-xs text-slate-400">MCDR / DGM Rajasthan year-wise plans</p>
            </div>
          </div>
          <Link
            href="/project/new"
            className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-amber-400"
          >
            <FilePlus className="h-4 w-4" />
            New project
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-10">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">
          Projects
        </h2>

        {projects.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center dark:border-slate-700 dark:bg-slate-900">
            <FolderOpen className="mx-auto h-10 w-10 text-slate-400" />
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
              No projects yet. Create your first one to begin.
            </p>
            <Link
              href="/project/new"
              className="mt-5 inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-amber-500 dark:text-slate-950 dark:hover:bg-amber-400"
            >
              <FilePlus className="h-4 w-4" />
              Create new mining plan project
            </Link>
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <li key={p.slug}>
                <Link
                  href={`/project/${p.slug}/1`}
                  className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {p.project_name}
                  </div>
                  {p.updated_at && (
                    <div className="mt-1 text-xs text-slate-500">
                      Updated {new Date(p.updated_at).toLocaleString()}
                    </div>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-12 text-xs text-slate-500">
          Generated plans are conceptual. Final statutory submission must be reviewed and signed by a
          qualified mining engineer / RQP / competent person.
        </p>
      </section>
    </main>
  );
}
