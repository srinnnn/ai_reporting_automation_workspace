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
import { useSearchParams } from "react-router-dom";
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
import type { BrandSummary, CategorySummary } from "../types/platform";

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

export function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data, error, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const brands = data?.brands ?? [];
  const projects = data?.projects ?? [];
  const selectedBrandKey = searchParams.get("brand") ?? brands[0]?.key ?? "";
  const selectedBrand = brands.find((brand) => brand.key === selectedBrandKey) ?? brands[0];
  const selectedBrandProjects = selectedBrand ? projects.filter((project) => project.brand_key === selectedBrand.key) : [];
  const selectedBrandCategories = selectedBrand?.categories ?? emptyCategories;
  const selectedBrandMetrics = buildSelectedBrandMetrics(selectedBrand, selectedBrandProjects.length);

  return (
    <div className="page">
      <PageHeader />
      <GlobalFilterBar />

      {isLoading ? <StateLine text="加载中" /> : null}
      {error ? <StateLine text="API 暂不可用，请稍后重试" /> : null}

      <BrandWorkspaceSection
        activeCategoryCount={selectedBrandMetrics.activeCategoryCount}
        brands={brands}
        capabilityCount={selectedBrandMetrics.capabilityCount}
        selectedBrand={selectedBrand}
        onSelect={(brandKey) => setSearchParams({ brand: brandKey })}
      />
      <MetricGrid metrics={selectedBrandMetrics.cards} />
      <CategoryGrid brand={selectedBrand} categories={selectedBrandCategories} />
      <ConnectedProjects brand={selectedBrand} projects={selectedBrandProjects} />
      <FeedbackPanel brand={selectedBrand} />
      <QuickActionGrid actions={quickActions} />

      <footer data-homepage-module="true" data-module="footer">Middle Platform Design Baseline V1.0</footer>
    </div>
  );
}

function StateLine({ text }: { text: string }) {
  return <div className="state-line">{text}</div>;
}

function buildSelectedBrandMetrics(brand: BrandSummary | undefined, projectCount: number) {
  const categories = brand?.categories ?? [];
  const activeCategoryCount = brand?.active_category_count ?? categories.filter((category) => category.capability_count > 0).length;
  const capabilityCount = categories.reduce((total, category) => total + category.capability_count, 0);
  return {
    activeCategoryCount,
    capabilityCount,
    cards: [
      { accent: "accent-slate", icon: IconDatabase, label: "已接分类", note: "当前品牌", testId: "kpi-active-categories", value: activeCategoryCount },
      { accent: "accent-sage", icon: IconFlag, label: "已接项目", note: "当前品牌", testId: "kpi-connected-projects", value: projectCount },
      { accent: "accent-lavender", icon: IconShieldCheck, label: "可见能力", note: "Workspace 内可见", testId: "kpi-capabilities", value: capabilityCount },
      { accent: "accent-amber", icon: IconCalendar, label: "反馈", note: "暂无数据源", testId: "kpi-feedback", value: "未接入" },
    ],
  };
}
