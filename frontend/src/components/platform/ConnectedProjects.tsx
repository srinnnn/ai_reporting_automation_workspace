import { IconArrowRight } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { BrandSummary, ProjectSummary } from "../../types/platform";
import { Badge } from "../ui";
import { EmptyState } from "./EmptyState";

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
  return (
    <Link className="project-row" data-testid={`project-${project.key}`} to={`/projects/${project.key}`}>
      <span className={`project-priority category-${project.category_key.toLowerCase()}`}>{project.category_key}</span>
      <strong>{project.name}</strong>
      <span>{project.brand_key}</span>
      <Badge variant="success">{project.status}</Badge>
      <IconArrowRight className="project-arrow" size={15} />
    </Link>
  );
}
