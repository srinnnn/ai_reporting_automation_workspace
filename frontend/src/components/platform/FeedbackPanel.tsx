import type { BrandSummary } from "../../types/platform";

export function FeedbackPanel({ brand }: { brand?: BrandSummary }) {
  return (
    <section className="panel feedback-panel" data-testid="developed-feedback" data-homepage-module="true" data-module="developed-feedback">
      <div className="section-title"><h2>已开发反馈汇总</h2><span>{brand?.name ?? "暂无品牌"} / 未接入</span></div>
      <div className="feedback-empty">
        <strong>当前品牌暂无反馈记录</strong>
        <p>反馈数据源接入后将在这里统一汇总。</p>
      </div>
    </section>
  );
}
