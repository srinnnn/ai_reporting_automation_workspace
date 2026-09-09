import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { ConnectedProjects } from "../components/platform";

type ModulePageProps = {
  title: string;
  moduleKey?: "tasks" | "reports" | "data-foundation" | "projects";
};

export function ModulePage({ title, moduleKey }: ModulePageProps) {
  const query = useQuery({
    queryKey: ["module", moduleKey],
    queryFn: () => moduleKey && moduleKey !== "projects" ? api.module(moduleKey) : Promise.resolve(undefined),
    enabled: Boolean(moduleKey && moduleKey !== "projects"),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: api.projects,
    enabled: moduleKey === "projects",
  });
  if (moduleKey === "projects") {
    return (
      <div className="page">
        <section className="page-header">
          <div><p className="eyebrow">Platform Projects</p><h1>{title}</h1><p>全部品牌 / 项目目录</p></div>
        </section>
        <ConnectedProjects
          dataModule="project-directory"
          emptyText={projectsQuery.isError ? "项目数据加载失败" : "暂无项目数据"}
          homepageModule={false}
          projects={projectsQuery.data ?? []}
          scopeLabel="全部品牌"
          testId="project-directory"
        />
      </div>
    );
  }
  return (
    <div className="page">
      <section className="page-header"><div><p className="eyebrow">Platform Route</p><h1>{title}</h1><p>Route、Layout、API Contract、Empty State 已建立。</p></div></section>
      <section className="panel">
        <h2>{query.data?.title ?? title}</h2>
        <p className="empty">{query.data?.message ?? "暂无真实业务数据，页面入口已保留。"}</p>
      </section>
    </div>
  );
}
