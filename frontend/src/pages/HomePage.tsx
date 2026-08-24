import { IconArrowRight, IconCalendar, IconFilter, IconPlus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { BrandSummary, ProjectSummary } from "../types/platform";

const emptyCategories = [
  { key: "P1", name: "数据提效" },
  { key: "P2", name: "内容提效" },
  { key: "P3", name: "配置提效" },
  { key: "P4", name: "复查" },
];

export function HomePage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const brands = data?.brands ?? [];
  const projects = data?.projects ?? [];
  const selectedBrand = brands[0];

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
      <section className="filter-bar">
        <span><IconFilter size={16} /> 全局筛选</span>
        <button>品牌</button>
        <button>优先级</button>
        <button>状态</button>
      </section>
      {isLoading ? <StateLine text="加载中" /> : null}
      {error ? <StateLine text="API 暂不可用，请稍后重试" /> : null}
      <BrandSelector brands={brands} />
      <BrandBanner brand={selectedBrand} />
      <KpiStrip brandCount={brands.length} projectCount={projects.length} />
      <CategoryEntry brand={selectedBrand} />
      <ProjectList projects={projects} />
      <FeedbackSummary />
      <QuickNav />
      <footer>Middle Platform Design Baseline V1.0</footer>
    </div>
  );
}

function StateLine({ text }: { text: string }) {
  return <div className="state-line">{text}</div>;
}

function BrandSelector({ brands }: { brands: BrandSummary[] }) {
  return (
    <section className="panel">
      <div className="section-title">
        <h2>品牌 Workspace 入口</h2>
        <span>{brands.length || 0} 个品牌</span>
      </div>
      <div className="brand-grid">
        {brands.length ? brands.map((brand) => (
          <Link className="brand-card" to={`/workspace/${brand.key}`} key={brand.key}>
            <strong>{brand.name}</strong>
            <span>{brand.tagline}</span>
            <em>进入工作台 <IconArrowRight size={14} /></em>
          </Link>
        )) : <EmptyText text="暂无品牌数据" />}
      </div>
    </section>
  );
}

function BrandBanner({ brand }: { brand?: BrandSummary }) {
  return (
    <section className="brand-banner">
      <div>
        <span>当前品牌</span>
        <strong>{brand?.name ?? "暂无数据"}</strong>
      </div>
      <p>{brand?.tagline ?? "Production 默认不加载 Demo 品牌数据。"}</p>
    </section>
  );
}

function KpiStrip({ brandCount, projectCount }: { brandCount: number; projectCount: number }) {
  return (
    <section className="kpi-grid">
      <article><span>品牌数</span><strong>{brandCount}</strong></article>
      <article><span>已接项目</span><strong>{projectCount}</strong></article>
      <article><span>运行任务</span><strong>0</strong></article>
      <article><span>异常</span><strong>0</strong></article>
    </section>
  );
}

function CategoryEntry({ brand }: { brand?: BrandSummary }) {
  const categories = brand?.categories ?? emptyCategories.map((item) => ({ ...item, capability_count: 0, status: "NOT_CONNECTED" }));
  return (
    <section className="panel">
      <div className="section-title">
        <h2>能力分类</h2>
        <span>仅展示入口，不展开全部能力</span>
      </div>
      <div className="category-grid">
        {categories.map((category) => (
          <Link className="category-card" to={brand ? `/workspace/${brand.key}/${category.key}` : "/workspace/UNKNOWN"} key={category.key}>
            <strong>{category.key}</strong>
            <span>{category.name}</span>
            <em>{category.capability_count} 个能力</em>
          </Link>
        ))}
      </div>
    </section>
  );
}

function ProjectList({ projects }: { projects: ProjectSummary[] }) {
  return (
    <section className="panel">
      <div className="section-title">
        <h2>已接项目</h2>
        <Link to="/projects">查看全部</Link>
      </div>
      <div className="project-list">
        {projects.length ? projects.slice(0, 5).map((project) => (
          <Link className="project-row" to={`/projects/${project.key}`} key={project.key}>
            <strong>{project.name}</strong>
            <span>{project.brand_key} / {project.category_key} / {project.status}</span>
          </Link>
        )) : <EmptyText text="暂无项目数据" />}
      </div>
    </section>
  );
}

function FeedbackSummary() {
  return (
    <section className="panel">
      <div className="section-title"><h2>已开发反馈汇总</h2><span>0 条</span></div>
      <EmptyText text="暂无反馈数据" />
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
