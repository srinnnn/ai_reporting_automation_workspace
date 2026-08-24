export type CategorySummary = {
  key: "P1" | "P2" | "P3" | "P4";
  name: string;
  capability_count: number;
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
