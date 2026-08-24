import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

export function CategoryPage() {
  const { brandKey = "", categoryKey = "" } = useParams();
  const { data, error } = useQuery({ queryKey: ["brand", brandKey], queryFn: () => api.brand(brandKey), retry: false });
  const category = data?.categories.find((item) => item.key === categoryKey);
  if (error || !data || !category) {
    return <div className="page"><section className="panel"><h1>未知分类</h1><p className="empty">当前品牌或分类不存在。</p></section></div>;
  }
  return (
    <div className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">品牌工作台 / {data.key} / {category.key}</p>
          <h1>{category.key} {category.name}</h1>
          <p>仅展示当前品牌与当前 P 分类下的能力列表。</p>
        </div>
        <Link className="text-link" to={`/workspace/${data.key}`}>返回工作台</Link>
      </section>
      <section className="panel">
        <div className="section-title"><h2>能力列表</h2><span>{category.capability_count} 个能力</span></div>
        {category.capability_count > 0 ? <article className="project-row"><strong>{data.name} {category.name}</strong><span>{category.status}</span></article> : <p className="empty">当前品牌暂无接入能力</p>}
      </section>
    </div>
  );
}
