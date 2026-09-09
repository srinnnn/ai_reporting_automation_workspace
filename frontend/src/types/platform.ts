export type CategorySummary = {
  key: "P1" | "P2" | "P3" | "P4";
  name: string;
  capability_count: number;
  status: string;
  capabilities: CapabilitySummary[];
};

export type CapabilitySummary = {
  key: string;
  name: string;
  brand_key: string;
  category_key: "P1" | "P2" | "P3" | "P4";
  status: string;
};

export type BrandSummary = {
  key: string;
  name: string;
  tagline: string;
  active_category_count: number;
  categories: CategorySummary[];
};

export type ProjectSummary = {
  key: string;
  name: string;
  brand_key: string;
  category_key: "P1" | "P2" | "P3" | "P4";
  status: string;
  integration_key?: string | null;
  entry_path?: string | null;
};

export type IntegrationHealth = {
  service: string;
  status: "AVAILABLE" | "UNAVAILABLE";
  entry_path: string;
  message: string;
};

export type FeedbackSummary = {
  project: string;
  mapped_project_key: string | null;
  mapped_project_name: string | null;
  brand_key: string | null;
  category_key: "P1" | "P2" | "P3" | "P4" | null;
  status: string;
  original_manual_time: string;
  current_processing_time: string;
  business_feedback: string;
  iteration_need: string;
  updated_by: string;
  updated_at: string;
};

export type DashboardSummary = {
  brands: BrandSummary[];
  projects: ProjectSummary[];
  kpis: Record<string, number | string>;
};

export type ScheduleItem = {
  key: string;
  name: string;
  brand_key: string;
  status: string;
  milestone: string;
  risk: string;
};

export type EmptyModule = {
  route: string;
  title: string;
  status: string;
  message: string;
};
