import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page">
      <section className="panel">
        <h1>404</h1>
        <p className="empty">页面不存在。</p>
        <Link className="text-link" to="/">返回首页</Link>
      </section>
    </div>
  );
}
