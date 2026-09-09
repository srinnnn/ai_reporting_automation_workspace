import { useQuery } from "@tanstack/react-query";
import { IconDatabase, IconExternalLink, IconForms } from "@tabler/icons-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { StatusDot } from "../components/platform";
import { Button } from "../components/ui";
import type { ProjectSummary } from "../types/platform";

export function ProjectPage() {
  const { projectKey = "" } = useParams();
  const { data, error } = useQuery({ queryKey: ["project", projectKey], queryFn: () => api.project(projectKey), retry: false });
  if (error || !data) {
    return <div className="page"><section className="panel"><h1>未知项目</h1><p className="empty">项目不存在或未接入。</p></section></div>;
  }
  if (data.integration_key === "private-data-local-center") {
    return <PrivateDataLocalCenterProject project={data} />;
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

function PrivateDataLocalCenterProject({ project }: { project: ProjectSummary }) {
  const { data: health, error, isPending } = useQuery({
    queryKey: ["integration-health", project.integration_key],
    queryFn: api.privateDataLocalCenterHealth,
    retry: false,
  });
  const available = !isPending && !error && health?.status === "AVAILABLE";
  const status = isPending ? "CHECKING" : available ? "AVAILABLE" : "UNAVAILABLE";
  const message = isPending ? "正在检查采集需求服务" : available ? health.message : "采集需求服务不可用";

  return (
    <div className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Project Workspace</p>
          <h1>{project.name}</h1>
          <p>{project.brand_key} / {project.category_key} / {project.status}</p>
        </div>
        <div className="header-actions">
          <Link className="text-link" to="/projects">返回项目管理</Link>
        </div>
      </section>
      <section className="panel integration-panel">
        <div className="section-title">
          <div className="integration-title">
            <span className="icon-tile"><IconForms size={19} /></span>
            <h2>采集需求入口</h2>
          </div>
          <StatusDot status={status} />
        </div>
        <p className="integration-message">{message}</p>
        <dl className="integration-meta">
          <div><dt>数据范围</dt><dd>私域商品、经营与自定义数据需求</dd></div>
          <div><dt>当前阶段</dt><dd>需求收集与本地保存</dd></div>
          <div><dt>存储边界</dt><dd><IconDatabase size={15} /> 独立本地数据库</dd></div>
        </dl>
        <div className="integration-actions">
          {available && project.entry_path ? (
            <Button asChild variant="primary">
              <a href={project.entry_path}>打开采集需求页 <IconExternalLink size={16} /></a>
            </Button>
          ) : (
            <Button disabled>{isPending ? "正在检查" : "服务不可用"}</Button>
          )}
        </div>
      </section>
    </div>
  );
}
