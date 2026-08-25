import { Link } from "react-router-dom";
import type { BrandSummary, ProjectSummary } from "../../types/platform";
import { Badge } from "../ui";
import { EmptyState } from "./EmptyState";
import { StatusDot } from "./StatusDot";
import { platformIcons } from "./iconSemantics";

type ConnectedProjectsProps = {
  brand?: BrandSummary;
  dataModule?: string;
  emptyText?: string;
  homepageModule?: boolean;
  projects: ProjectSummary[];
  scopeLabel?: string;
  testId?: string;
};

export function ConnectedProjects({
  brand,
  dataModule = "global-projects",
  emptyText = "当前筛选范围暂无项目数据",
  homepageModule = true,
  projects,
  scopeLabel,
  testId = "connected-projects",
}: ConnectedProjectsProps) {
  return (
    <section className="panel project-panel" data-testid={testId} {...(homepageModule ? { "data-homepage-module": "true" } : {})} data-module={dataModule}>
      <div className="section-title">
        <h2>已接项目</h2>
        <span>{scopeLabel ?? brand?.name ?? "全部品牌"} / {projects.length} 项</span>
      </div>
      <div className="project-list">
        {projects.length ? projects.slice(0, 8).map((project) => (
          <ProjectRow project={project} key={project.key} />
        )) : <EmptyState text={emptyText} />}
      </div>
    </section>
  );
}

export function ProjectRow({ project }: { project: ProjectSummary }) {
  const ActionIcon = platformIcons.action;
  return (
    <Link className="project-row" data-testid={`project-${project.key}`} to={`/projects/${project.key}`}>
      <Badge className={`category-badge category-badge-${project.category_key.toLowerCase()}`}>{project.category_key}</Badge>
      <div className="project-row-copy">
        <strong>{project.name}</strong>
        <span>{project.category_key} 分类能力</span>
      </div>
      <span className="project-brand-meta">{project.brand_key}</span>
      <StatusDot status={project.status} />
      <ActionIcon className="project-arrow" size={15} />
    </Link>
  );
}
