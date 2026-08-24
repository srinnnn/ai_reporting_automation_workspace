import {
  IconArrowRight,
  IconCalendar,
  IconDatabase,
  IconFilter,
  IconFlag,
  IconPlayerPlay,
  IconPlus,
  IconReportAnalytics,
  IconShieldCheck,
  IconTimeline,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { BrandSummary, ProjectSummary } from "../types/platform";

const emptyCategories = [
  { key: "P1", name: "数据提效" },
  { key: "P2", name: "内容提效" },
  { key: "P3", name: "配置提效" },
  { key: "P4", name: "复查" },
];

export function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data, isLoading, error } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const brands = data?.brands ?? [];
  const projects = data?.projects ?? [];
  const selectedBrandKey = searchParams.get("brand") ?? brands[0]?.key ?? "";
  const selectedBrand = brands.find((brand) => brand.key === selectedBrandKey) ?? brands[0];
  const selectedBrandProjects = selectedBrand ? projects.filter((project) => project.brand_key === selectedBrand.key) : [];

  return (
    <div className="page">
      <section className="page-header" data-homepage-module="true" data-module="page-header">
        <div>
          <p className="eyebrow">品牌工作台 / Brand Workspace Overview</p>
          <h1>中台全局首页</h1>
          <p>首页展示核心概览与分类入口，不展开全部能力。</p>
        </div>
        <div className="header-actions">
          <button><IconCalendar size={16} /> 今天</button>
          <button className="primary"><IconPlus size={16} /> 新建任务</button>
        </div>
      </section>

      <section className="filter-bar" data-testid="global-filters" data-homepage-module="true" data-module="global-filters">
        <span><IconFilter size={16} /> 全局筛选</span>
        <button>项目</button>
        <button>品牌</button>
        <button>优先级</button>
        <button>状态</button>
      </section>

      {isLoading ? <StateLine text="加载中" /> : null}
      {error ? <StateLine text="API 暂不可用，请稍后重试" /> : null}

      <BrandSelector
        brands={brands}
        selectedBrand={selectedBrand}
        onSelect={(brandKey) => setSearchParams({ brand: brandKey })}
      />

      <KpiStrip brand={selectedBrand} projects={selectedBrandProjects} />
      <CategoryEntry brand={selectedBrand} />
      <ProjectList brand={selectedBrand} projects={selectedBrandProjects} />
      <FeedbackSummary brand={selectedBrand} />
      <QuickNav />

      <footer data-homepage-module="true" data-module="footer">Middle Platform Design Baseline V1.0</footer>
    </div>
  );
}

function StateLine({ text }: { text: string }) {
  return <div className="state-line">{text}</div>;
}

function BrandSelector({
  brands,
  selectedBrand,
  onSelect,
}: {
  brands: BrandSummary[];
  selectedBrand?: BrandSummary;
  onSelect: (brandKey: string) => void;
}) {
  return (
    <section className="panel brand-workspace-panel" data-testid="brand-workspace-entry" data-homepage-module="true" data-module="brand-workspace">
      <div className="section-title">
        <h2>品牌 Workspace 入口</h2>
        <span>{brands.length || 0} 个品牌</span>
      </div>
      {brands.length ? (
        <>
          <label className="brand-select-label" htmlFor="brand-selector">品牌</label>
          <select
            id="brand-selector"
            className="brand-select"
            value={selectedBrand?.key ?? brands[0].key}
            onChange={(event) => onSelect(event.target.value)}
          >
            {brands.map((brand) => <option value={brand.key} key={brand.key}>{brand.name}</option>)}
          </select>
          <BrandBanner brand={selectedBrand ?? brands[0]} />
        </>
      ) : <EmptyText text="暂无品牌数据" />}
    </section>
  );
}

function BrandBanner({ brand }: { brand?: BrandSummary }) {
  const activeCount = brand?.active_category_count ?? 0;
  const capabilityCount = brand?.categories.reduce((total, category) => total + category.capability_count, 0) ?? 0;
  const monogram = brand?.key.slice(0, 1) ?? "-";
  return (
    <section className="brand-banner" data-testid="selected-brand-banner">
      <div className="brand-monogram" aria-hidden="true">{monogram}</div>
      <div className="brand-banner-copy">
        <span>当前品牌</span>
        <strong>{brand?.name ?? "暂无数据"}</strong>
        <p>{brand?.tagline ?? "Production 默认不加载 Demo 品牌数据。"}</p>
        <em>{activeCount} 个分类 · {capabilityCount} 个能力</em>
      </div>
      <div className="brand-banner-meta">
        <span>已接分类</span>
        <strong>{activeCount}</strong>
      </div>
      {brand ? <Link className="text-link brand-enter-link" to={`/workspace/${brand.key}`}>进入 Workspace <IconArrowRight size={14} /></Link> : null}
    </section>
  );
}

function KpiStrip({ brand, projects }: { brand?: BrandSummary; projects: ProjectSummary[] }) {
  const categories = brand?.categories ?? [];
  const activeCategoryCount = brand?.active_category_count ?? categories.filter((category) => category.capability_count > 0).length;
  const capabilityCount = categories.reduce((total, category) => total + category.capability_count, 0);
  return (
    <section className="kpi-grid" data-testid="selected-brand-kpi" data-homepage-module="true" data-module="selected-brand-kpi">
      <article className="kpi-card accent-slate" data-testid="kpi-active-categories"><IconDatabase size={18} /><span>已接分类</span><strong>{activeCategoryCount}</strong><em>当前品牌</em></article>
      <article className="kpi-card accent-sage" data-testid="kpi-connected-projects"><IconFlag size={18} /><span>已接项目</span><strong>{projects.length}</strong><em>当前品牌</em></article>
      <article className="kpi-card accent-lavender" data-testid="kpi-capabilities"><IconShieldCheck size={18} /><span>可见能力</span><strong>{capabilityCount}</strong><em>Workspace 内可见</em></article>
      <article className="kpi-card accent-amber" data-testid="kpi-feedback"><IconCalendar size={18} /><span>反馈</span><strong>0</strong><em>暂无记录</em></article>
    </section>
  );
}

function CategoryEntry({ brand }: { brand?: BrandSummary }) {
  const categories = brand?.categories ?? emptyCategories.map((item) => ({ ...item, capability_count: 0, status: "NOT_CONNECTED", capabilities: [] }));
  return (
    <section className="panel category-panel" data-testid="p1-p4-category-grid" data-homepage-module="true" data-module="p1-p4">
      <div className="section-title">
        <h2>P1-P4 分级入口</h2>
        <span>仅展示入口，不展开全部能力</span>
      </div>
      <div className="category-grid">
        {categories.map((category) => (
          <Link
            className={`category-card category-${category.key.toLowerCase()}`}
            data-testid={`category-${category.key}`}
            to={brand ? `/workspace/${brand.key}/${category.key}` : "/workspace/UNKNOWN"}
            key={category.key}
          >
            <strong>{category.key}</strong>
            <span>{category.name}</span>
            <em>{category.capability_count > 0 ? `${category.capability_count} 个能力` : "暂无接入能力"}</em>
            <small>进入分级 <IconArrowRight size={13} /></small>
          </Link>
        ))}
      </div>
    </section>
  );
}

function ProjectList({ brand, projects }: { brand?: BrandSummary; projects: ProjectSummary[] }) {
  return (
    <section className="panel project-panel" data-testid="connected-projects" data-homepage-module="true" data-module="connected-projects">
      <div className="section-title">
        <h2>已接项目</h2>
        <span>{brand?.name ?? "暂无品牌"} / {projects.length} 项</span>
      </div>
      <div className="project-list">
        {projects.length ? projects.slice(0, 5).map((project) => (
          <Link className="project-row" data-testid={`project-${project.key}`} to={`/projects/${project.key}`} key={project.key}>
            <span className={`project-priority category-${project.category_key.toLowerCase()}`}>{project.category_key}</span>
            <strong>{project.name}</strong>
            <span>{project.brand_key}</span>
            <em>{project.status}</em>
            <IconArrowRight className="project-arrow" size={15} />
          </Link>
        )) : <EmptyText text="当前品牌暂无项目数据" />}
      </div>
    </section>
  );
}

function FeedbackSummary({ brand }: { brand?: BrandSummary }) {
  return (
    <section className="panel feedback-panel" data-testid="developed-feedback" data-homepage-module="true" data-module="developed-feedback">
      <div className="section-title"><h2>已开发反馈汇总</h2><span>{brand?.name ?? "暂无品牌"} / 0 条</span></div>
      <div className="feedback-empty">
        <strong>当前品牌暂无反馈记录</strong>
        <p>业务反馈产生后将在这里统一汇总。</p>
      </div>
    </section>
  );
}

function QuickNav() {
  const actions = [
    { to: "/data-foundation", title: "数据入库", description: "导入并管理业务数据", icon: IconDatabase, accent: "accent-slate" },
    { to: "/tasks", title: "自动化执行", description: "运行已接入自动化任务", icon: IconPlayerPlay, accent: "accent-sage" },
    { to: "/reports", title: "查看报表", description: "查看数据与结果", icon: IconReportAnalytics, accent: "accent-lavender" },
    { to: "/schedule", title: "开发排期", description: "查看项目开发状态", icon: IconTimeline, accent: "accent-amber" },
  ];
  return (
    <section className="quick-nav" data-testid="quick-navigation" data-homepage-module="true" data-module="quick-navigation">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <Link className={`quick-action ${action.accent}`} to={action.to} key={action.to}>
            <Icon size={18} />
            <strong>{action.title}</strong>
            <span>{action.description}</span>
          </Link>
        );
      })}
    </section>
  );
}

function EmptyText({ text }: { text: string }) {
  return <p className="empty">{text}</p>;
}
