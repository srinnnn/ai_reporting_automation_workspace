import type { BrandSummary, DashboardSummary, EmptyModule, ProjectSummary, ScheduleItem } from "../types/platform";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  dashboard: () => getJson<DashboardSummary>("/api/v1/dashboard"),
  brands: () => getJson<BrandSummary[]>("/api/v1/brands"),
  brand: (brandKey: string) => getJson<BrandSummary>(`/api/v1/brands/${encodeURIComponent(brandKey)}`),
  projects: () => getJson<ProjectSummary[]>("/api/v1/projects"),
  project: (projectKey: string) => getJson<ProjectSummary>(`/api/v1/projects/${encodeURIComponent(projectKey)}`),
  schedules: () => getJson<ScheduleItem[]>("/api/v1/schedules"),
  module: (key: "tasks" | "reports" | "data-foundation") => getJson<EmptyModule>(`/api/v1/${key}`),
};
