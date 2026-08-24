import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

export function ProjectPage() {
  const { projectKey = "" } = useParams();
  const { data, error } = useQuery({ queryKey: ["project", projectKey], queryFn: () => api.project(projectKey), retry: false });
  if (error || !data) {
    return <div className="page"><section className="panel"><h1>未知项目</h1><p className="empty">项目不存在或未接入。</p></section></div>;
  }
  return (
    <div className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Project Workspace</p>
          <h1>{data.name}</h1>
          <p>{data.brand_key} / {data.category_key} / {data.status}</p>
        </div>
        <Link className="text-link" to="/projects">返回项目管理</Link>
      </section>
      <section className="panel-grid">
        {["Overview", "Input", "Output", "Configuration", "Run", "Task History", "Feedback", "Schedule", "Version"].map((title) => (
          <article className="panel" key={title}><h2>{title}</h2><p className="empty">NOT_CONNECTED</p></article>
        ))}
      </section>
    </div>
  );
}
