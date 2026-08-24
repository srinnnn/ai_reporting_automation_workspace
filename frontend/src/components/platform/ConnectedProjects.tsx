import { IconArrowRight } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { BrandSummary, ProjectSummary } from "../../types/platform";
import { Badge } from "../ui";
import { EmptyState } from "./EmptyState";

type ConnectedProjectsProps = {
  brand?: BrandSummary;
  projects: ProjectSummary[];
};

export function ConnectedProjects({ brand, projects }: ConnectedProjectsProps) {
  return (
    <section className="panel project-panel" data-testid="connected-projects" data-homepage-module="true" data-module="connected-projects">
      <div className="section-title">
        <h2>已接项目</h2>
        <span>{brand?.name ?? "暂无品牌"} / {projects.length} 项</span>
      </div>
      <div className="project-list">
        {projects.length ? projects.slice(0, 5).map((project) => (
          <ProjectRow project={project} key={project.key} />
        )) : <EmptyState text="当前品牌暂无项目数据" />}
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
