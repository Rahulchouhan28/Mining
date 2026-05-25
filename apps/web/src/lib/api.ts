import type { MiningPlanProject, ProjectListItem } from "./types";

// On the server we call FastAPI directly (skip Next.js rewrite to save a hop).
// On the client we use the same /api/* origin (Next.js proxies it).
function baseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.FASTAPI_ORIGIN ?? "http://127.0.0.1:8000";
  }
  return ""; // same-origin
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${baseUrl()}${path}`;
  const res = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init?.body ? { "content-type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return (await res.json()) as T;
}

export async function listProjects(): Promise<ProjectListItem[]> {
  try {
    return await request<ProjectListItem[]>("/api/projects");
  } catch {
    return [];
  }
}

export async function getProject(slug: string): Promise<MiningPlanProject & { slug: string }> {
  return request(`/api/projects/${encodeURIComponent(slug)}`);
}

export async function createProject(
  payload: MiningPlanProject,
): Promise<MiningPlanProject & { slug: string }> {
  return request("/api/projects", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateProject(
  slug: string,
  payload: MiningPlanProject,
): Promise<MiningPlanProject & { slug: string }> {
  return request(`/api/projects/${encodeURIComponent(slug)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function generatePlan(slug: string, alternatives: string[]): Promise<unknown> {
  return request(`/api/projects/${encodeURIComponent(slug)}/generate`, {
    method: "POST",
    body: JSON.stringify({ alternatives }),
  });
}

export async function bufferGeometry(geometry: GeoJSON.Geometry, distance_m: number) {
  return request<{ geometry: GeoJSON.Geometry | null; area_m2: number }>("/api/gis/buffer", {
    method: "POST",
    body: JSON.stringify({ geometry, distance_m }),
  });
}
