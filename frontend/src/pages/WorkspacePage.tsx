import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import {
  BrandSelector,
  CategoryGrid,
  ConnectedProjects,
  FeedbackPanel,
  MetricGrid,
} from "../components/platform";
import { platformIcons } from "../components/platform/iconSemantics";
import type { BrandSummary, ProjectSummary } from "../types/platform";

export function WorkspacePage() {
  const { brandKey = "" } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, error } = useQuery({ queryKey: ["brand", brandKey], queryFn: () => api.brand(brandKey), retry: false });
  const brandsQuery = useQuery({ queryKey: ["brands"], queryFn: api.brands });
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  if (isLoading) return <div className="page"><p className="empty">加载中</p></div>;
  if (error || !data) return <Unknown title="未知品牌" />;
  const brands = brandsQuery.data ?? [data];
  const projects = projectsQuery.data ?? [];
  const brandProjects = projects.filter((project) => project.brand_key === data.key);
  const metrics = buildBrandMetrics(data, brandProjects);
  return (
    <div className="page">
      <section className="page-header" data-module="brand-header">
        <div className="workspace-heading">
          <div className="brand-monogram brand-monogram-sm" aria-hidden="true">{data.key.slice(0, 1)}</div>
          <div>
            <p className="eyebrow">品牌工作台 / {data.key}</p>
            <h1>{data.name}</h1>
            <p>{data.tagline}</p>
          </div>
        </div>
        <Link className="text-link" to="/">返回首页</Link>
      </section>

      <section className="panel brand-context-panel" data-testid="brand-context" data-module="brand-context">
        <div className="section-title">
          <h2>品牌上下文</h2>
          <span>{data.key}</span>
        </div>
        <BrandSelector brands={brands} selectedBrand={data} onSelect={(nextBrandKey) => navigate(`/workspace/${nextBrandKey}`)} />
      </section>

      <MetricGrid dataModule="brand-kpi" homepageModule={false} metrics={metrics} testId="brand-kpi" />
      <CategoryGrid
        brand={data}
        categories={data.categories}
        dataModule="brand-p1-p4"
        homepageModule={false}
        title="品牌 P1-P4"
        subtitle="仅展示当前品牌的能力分类"
      />
      <ConnectedProjects
        brand={data}
        dataModule="brand-projects"
        emptyText="当前品牌暂无项目数据"
        homepageModule={false}
        projects={brandProjects}
        testId="brand-projects"
      />
      <FeedbackPanel
        brand={data}
        dataModule="brand-feedback"
        emptyTitle="当前品牌暂无反馈记录"
        emptyDescription="反馈数据源接入后将在品牌工作台内按品牌汇总。"
        homepageModule={false}
        testId="brand-feedback"
      />
    </div>
  );
}

function buildBrandMetrics(brand: BrandSummary, projects: ProjectSummary[]) {
  const capabilityCount = brand.categories.reduce((total, category) => total + category.capability_count, 0);
  return [
    { accent: "accent-slate", icon: platformIcons.category, label: "已接分类", note: "当前品牌", testId: "kpi-active-categories", value: brand.active_category_count },
    { accent: "accent-sage", icon: platformIcons.project, label: "已接项目", note: "当前品牌", testId: "kpi-connected-projects", value: projects.length },
    { accent: "accent-lavender", icon: platformIcons.brandWorkspace, label: "可见能力", note: "Workspace 内可见", testId: "kpi-capabilities", value: capabilityCount },
    { accent: "accent-amber", icon: platformIcons.feedback, label: "反馈", note: "暂无数据源", testId: "kpi-feedback", value: "未接入" },
  ];
}

function Unknown({ title }: { title: string }) {
  return (
    <div className="page">
      <section className="panel">
        <h1>{title}</h1>
        <p className="empty">未找到对应数据或 Production 未启用 Demo 数据。</p>
        <Link className="text-link" to="/">返回首页</Link>
      </section>
    </div>
  );
}
