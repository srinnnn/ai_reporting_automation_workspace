import {
  IconArrowRight,
  IconCalendar,
  IconDatabase,
  IconFilter,
  IconFlag,
  IconPlus,
  IconShieldCheck,
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
      <section className="page-header">
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

      <section className="filter-bar" data-testid="global-filters">
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

      <footer>Middle Platform Design Baseline V1.0</footer>
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
    <section className="panel brand-workspace-panel" data-testid="brand-workspace-entry">
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
  return (
    <section className="brand-banner" data-testid="selected-brand-banner">
      <div className="brand-banner-copy">
        <span>当前品牌</span>
        <strong>{brand?.name ?? "暂无数据"}</strong>
        <p>{brand?.tagline ?? "Production 默认不加载 Demo 品牌数据。"}</p>
      </div>
      <div className="brand-banner-meta">
        <span>已接分类</span>
        <strong>{activeCount}</strong>
      </div>
      {brand ? <Link className="text-link brand-enter-link" to={`/workspace/${brand.key}`}>进入 Brand Workspace <IconArrowRight size={14} /></Link> : null}
    </section>
  );
}

function KpiStrip({ brand, projects }: { brand?: BrandSummary; projects: ProjectSummary[] }) {
  const categories = brand?.categories ?? [];
  const activeCategoryCount = brand?.active_category_count ?? categories.filter((category) => category.capability_count > 0).length;
  const capabilityCount = categories.reduce((total, category) => total + category.capability_count, 0);
  return (
    <section className="kpi-grid">
      <article data-testid="kpi-active-categories"><IconDatabase size={18} /><span>已接分类</span><strong>{activeCategoryCount}</strong></article>
      <article data-testid="kpi-connected-projects"><IconFlag size={18} /><span>已接项目</span><strong>{projects.length}</strong></article>
      <article data-testid="kpi-capabilities"><IconShieldCheck size={18} /><span>可见能力</span><strong>{capabilityCount}</strong></article>
      <article data-testid="kpi-feedback"><IconCalendar size={18} /><span>反馈</span><strong>0</strong></article>
    </section>
  );
}

function CategoryEntry({ brand }: { brand?: BrandSummary }) {
  const categories = brand?.categories ?? emptyCategories.map((item) => ({ ...item, capability_count: 0, status: "NOT_CONNECTED", capabilities: [] }));
  return (
    <section className="panel">
      <div className="section-title">
        <h2>能力分类</h2>
        <span>仅展示入口，不展开全部能力</span>
      </div>
      <div className="category-grid">
        {categories.map((category) => (
          <Link
            className="category-card"
            data-testid={`category-${category.key}`}
            to={brand ? `/workspace/${brand.key}/${category.key}` : "/workspace/UNKNOWN"}
            key={category.key}
          >
            <strong>{category.key}</strong>
            <span>{category.name}</span>
            <em>{category.capability_count} 个能力</em>
            <small><b>已接入</b>{category.capability_count}</small>
            <small><b>待接入</b>0</small>
          </Link>
        ))}
      </div>
    </section>
  );
}

function ProjectList({ brand, projects }: { brand?: BrandSummary; projects: ProjectSummary[] }) {
  return (
    <section className="panel">
      <div className="section-title">
        <h2>已接项目</h2>
        <span>{brand?.name ?? "暂无品牌"} / {projects.length} 项</span>
      </div>
      <div className="project-list">
        {projects.length ? projects.slice(0, 5).map((project) => (
          <Link className="project-row" data-testid={`project-${project.key}`} to={`/projects/${project.key}`} key={project.key}>
            <span className="project-priority">{project.category_key}</span>
            <strong>{project.name}</strong>
            <span>{project.brand_key} / {project.status}</span>
          </Link>
        )) : <EmptyText text="当前品牌暂无项目数据" />}
      </div>
    </section>
  );
}

function FeedbackSummary({ brand }: { brand?: BrandSummary }) {
  return (
    <section className="panel">
      <div className="section-title"><h2>已开发反馈汇总</h2><span>{brand?.name ?? "暂无品牌"} / 0 条</span></div>
      <EmptyText text="当前品牌暂无反馈数据" />
    </section>
  );
}

function QuickNav() {
  return (
    <section className="quick-nav">
      <Link to="/data-foundation">数据入库</Link>
      <Link to="/tasks">自动化执行</Link>
      <Link to="/reports">查看报表</Link>
      <Link to="/schedule">开发排期</Link>
    </section>
  );
}

function EmptyText({ text }: { text: string }) {
  return <p className="empty">{text}</p>;
}
