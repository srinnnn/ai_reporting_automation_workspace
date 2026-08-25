import type { BrandSummary } from "../../types/platform";

type FeedbackPanelProps = {
  brand?: BrandSummary;
  dataModule?: string;
  emptyDescription?: string;
  emptyTitle?: string;
  homepageModule?: boolean;
  scopeLabel?: string;
  testId?: string;
};

export function FeedbackPanel({
  brand,
  dataModule = "global-feedback",
  emptyDescription = "业务反馈接入后将在此统一汇总。",
  emptyTitle = "当前暂无已接入的开发反馈数据",
  homepageModule = true,
  scopeLabel,
  testId = "developed-feedback",
}: FeedbackPanelProps) {
  return (
    <section className="panel feedback-panel" data-testid={testId} {...(homepageModule ? { "data-homepage-module": "true" } : {})} data-module={dataModule}>
      <div className="section-title"><h2>已开发反馈汇总</h2><span>{scopeLabel ?? brand?.name ?? "全部品牌"} / 未接入</span></div>
      <div className="feedback-empty">
        <strong>{emptyTitle}</strong>
        <p>{emptyDescription}</p>
      </div>
    </section>
  );
}
