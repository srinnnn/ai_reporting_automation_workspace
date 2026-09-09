import type { BrandSummary, DashboardSummary, EmptyModule, FeedbackSummary, IntegrationHealth, ProjectSummary, ScheduleItem } from "../types/platform";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

type FeedbackFilters = Partial<Record<"brand" | "category" | "project" | "status", string>>;

function feedbackPath(filters: FeedbackFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/api/v1/feedback?${query}` : "/api/v1/feedback";
}

export const api = {
  dashboard: () => getJson<DashboardSummary>("/api/v1/dashboard"),
  brands: () => getJson<BrandSummary[]>("/api/v1/brands"),
  brand: (brandKey: string) => getJson<BrandSummary>(`/api/v1/brands/${encodeURIComponent(brandKey)}`),
  projects: () => getJson<ProjectSummary[]>("/api/v1/projects"),
  project: (projectKey: string) => getJson<ProjectSummary>(`/api/v1/projects/${encodeURIComponent(projectKey)}`),
  privateDataLocalCenterHealth: () => getJson<IntegrationHealth>("/api/v1/integrations/private-data-local-center/health"),
  feedback: (filters: FeedbackFilters = {}) => getJson<FeedbackSummary[]>(feedbackPath(filters)),
  schedules: () => getJson<ScheduleItem[]>("/api/v1/schedules"),
  module: (key: "tasks" | "reports" | "data-foundation") => getJson<EmptyModule>(`/api/v1/${key}`),
};
