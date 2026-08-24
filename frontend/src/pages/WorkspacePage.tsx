import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

export function WorkspacePage() {
  const { brandKey = "" } = useParams();
  const { data, isLoading, error } = useQuery({ queryKey: ["brand", brandKey], queryFn: () => api.brand(brandKey), retry: false });
  if (isLoading) return <div className="page"><p className="empty">加载中</p></div>;
  if (error || !data) return <Unknown title="未知品牌" />;
  return (
    <div className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">品牌工作台 / {data.key}</p>
          <h1>{data.name}</h1>
          <p>{data.tagline}</p>
        </div>
        <Link className="text-link" to="/">返回首页</Link>
      </section>
      <section className="kpi-grid">
        <article><span>已接分类</span><strong>{data.active_category_count}</strong></article>
        <article><span>运行中</span><strong>0</strong></article>
        <article><span>异常</span><strong>0</strong></article>
        <article><span>更新时间</span><strong>--</strong></article>
      </section>
      <section className="panel">
        <div className="section-title"><h2>分类入口</h2><span>only category entry</span></div>
        <div className="category-grid">
          {data.categories.map((category) => (
            <Link className="category-card" to={`/workspace/${data.key}/${category.key}`} key={category.key}>
              <strong>{category.key}</strong>
              <span>{category.name}</span>
              <em>{category.capability_count} 个能力</em>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
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
