import {
  IconCalendar,
  IconDatabase,
  IconFlag,
  IconPlayerPlay,
  IconReportAnalytics,
  IconShieldCheck,
  IconTimeline,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../api/client";
import {
  BrandWorkspaceSection,
  CategoryGrid,
  ConnectedProjects,
  FeedbackPanel,
  GlobalFilterBar,
  MetricGrid,
  PageHeader,
  QuickActionGrid,
} from "../components/platform";
import type { GlobalFilters } from "../components/platform/GlobalFilterBar";
import type { BrandSummary, CategorySummary, ProjectSummary } from "../types/platform";

const emptyCategories: CategorySummary[] = [
  { key: "P1", name: "数据提效", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
  { key: "P2", name: "内容提效", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
  { key: "P3", name: "配置提效", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
  { key: "P4", name: "复查", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
];

const quickActions = [
  { to: "/data-foundation", title: "数据入库", description: "导入并管理业务数据", icon: IconDatabase, accent: "accent-slate" },
  { to: "/tasks", title: "自动化执行", description: "运行已接入自动化任务", icon: IconPlayerPlay, accent: "accent-sage" },
  { to: "/reports", title: "查看报表", description: "查看数据与结果", icon: IconReportAnalytics, accent: "accent-lavender" },
  { to: "/schedule", title: "开发排期", description: "查看项目开发状态", icon: IconTimeline, accent: "accent-amber" },
];

const allFilterValue = "ALL";
const defaultGlobalFilters: GlobalFilters = {
  brandKey: allFilterValue,
  categoryKey: allFilterValue,
  projectKey: allFilterValue,
  status: allFilterValue,
};

export function HomePage() {
  const [globalFilters, setGlobalFilters] = useState<GlobalFilters>(defaultGlobalFilters);
  const [workspaceEntryBrandKey, setWorkspaceEntryBrandKey] = useState("");
  const { data, error, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const brands = data?.brands ?? [];
  const projects = data?.projects ?? [];
  const workspaceEntryBrand = brands.find((brand) => brand.key === workspaceEntryBrandKey) ?? brands[0];
  const filteredProjects = useMemo(() => filterProjects(projects, globalFilters), [globalFilters, projects]);
  const globalCategories = useMemo(() => buildGlobalCategories(filteredProjects), [filteredProjects]);
  const globalMetrics = useMemo(() => buildGlobalMetrics(filteredProjects, globalCategories), [filteredProjects, globalCategories]);
  const globalScopeLabel = buildGlobalScopeLabel(globalFilters, brands, projects);

  return (
    <div className="page">
      <PageHeader />
      <GlobalFilterBar brands={brands} filters={globalFilters} onChange={setGlobalFilters} projects={projects} />

      {isLoading ? <StateLine text="加载中" /> : null}
      {error ? <StateLine text="API 暂不可用，请稍后重试" /> : null}

      <BrandWorkspaceSection
        brands={brands}
        selectedBrand={workspaceEntryBrand}
        onSelect={setWorkspaceEntryBrandKey}
      />
      <MetricGrid metrics={globalMetrics.cards} />
      <CategoryGrid categories={globalCategories} />
      <ConnectedProjects projects={filteredProjects} scopeLabel={globalScopeLabel} />
      <FeedbackPanel
        scopeLabel={globalScopeLabel}
        emptyTitle="当前暂无已接入的开发反馈数据"
        emptyDescription="业务反馈接入后将在中台全局统一汇总。"
      />
      <QuickActionGrid actions={quickActions} />

      <footer data-homepage-module="true" data-module="footer">Middle Platform Design Baseline V1.0</footer>
    </div>
  );
}

function StateLine({ text }: { text: string }) {
  return <div className="state-line">{text}</div>;
}

function filterProjects(projects: ProjectSummary[], filters: GlobalFilters) {
  return projects.filter((project) => {
    if (filters.projectKey !== allFilterValue && project.key !== filters.projectKey) return false;
    if (filters.brandKey !== allFilterValue && project.brand_key !== filters.brandKey) return false;
    if (filters.categoryKey !== allFilterValue && project.category_key !== filters.categoryKey) return false;
    if (filters.status !== allFilterValue && project.status !== filters.status) return false;
    return true;
  });
}

function buildGlobalCategories(projects: ProjectSummary[]): CategorySummary[] {
  return emptyCategories.map((category) => ({
    ...category,
    capability_count: projects.filter((project) => project.category_key === category.key).length,
    status: projects.some((project) => project.category_key === category.key) ? "CONNECTED" : "NOT_CONNECTED",
  }));
}

function buildGlobalMetrics(projects: ProjectSummary[], categories: CategorySummary[]) {
  const brandCount = new Set(projects.map((project) => project.brand_key)).size;
  const activeCategoryCount = categories.filter((category) => category.capability_count > 0).length;
  return {
    cards: [
      { accent: "accent-slate", icon: IconDatabase, label: "已接品牌", note: "当前全局范围", testId: "kpi-brand-count", value: brandCount },
      { accent: "accent-sage", icon: IconFlag, label: "已接项目", note: "当前全局范围", testId: "kpi-connected-projects", value: projects.length },
      { accent: "accent-lavender", icon: IconShieldCheck, label: "已接分类", note: "当前全局范围", testId: "kpi-active-categories", value: activeCategoryCount },
      { accent: "accent-amber", icon: IconCalendar, label: "反馈", note: "暂无数据源", testId: "kpi-feedback", value: "未接入" },
    ],
  };
}

function buildGlobalScopeLabel(filters: GlobalFilters, brands: BrandSummary[], projects: ProjectSummary[]) {
  const parts: string[] = [];
  if (filters.brandKey !== allFilterValue) {
    parts.push(brands.find((brand) => brand.key === filters.brandKey)?.name ?? filters.brandKey);
  }
  if (filters.categoryKey !== allFilterValue) {
    parts.push(filters.categoryKey);
  }
  if (filters.projectKey !== allFilterValue) {
    parts.push(projects.find((project) => project.key === filters.projectKey)?.name ?? filters.projectKey);
  }
  if (filters.status !== allFilterValue) {
    parts.push(filters.status);
  }
  return parts.length ? parts.join(" / ") : "全部品牌";
}
