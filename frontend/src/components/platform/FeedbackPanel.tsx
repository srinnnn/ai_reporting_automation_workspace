import type { BrandSummary, FeedbackSummary } from "../../types/platform";
import { Badge } from "../ui";
import { IconTile } from "./IconTile";
import { platformIcons } from "./iconSemantics";

type FeedbackPanelProps = {
  brand?: BrandSummary;
  dataModule?: string;
  emptyDescription?: string;
  emptyTitle?: string;
  homepageModule?: boolean;
  records?: FeedbackSummary[];
  scopeLabel?: string;
  testId?: string;
};

export function FeedbackPanel({
  brand,
  dataModule = "global-feedback",
  emptyDescription = "业务反馈接入后将在此统一汇总。",
  emptyTitle = "当前暂无已接入的开发反馈数据",
  homepageModule = true,
  records = [],
  scopeLabel,
  testId = "developed-feedback",
}: FeedbackPanelProps) {
  return (
    <section className="panel feedback-panel" data-testid={testId} {...(homepageModule ? { "data-homepage-module": "true" } : {})} data-module={dataModule}>
      <div className="section-title"><h2>已开发反馈汇总</h2><span>{scopeLabel ?? brand?.name ?? "全部品牌"} / {records.length} 条</span></div>
      {records.length ? (
        <div aria-label="反馈记录横向列表" className="feedback-list" role="region" tabIndex={0}>
          {records.map((record) => <FeedbackRecordCard key={record.project} record={record} />)}
        </div>
      ) : (
        <div className="feedback-empty">
          <IconTile accent="accent-amber" icon={platformIcons.feedback} />
          <strong>{emptyTitle}</strong>
          <p>{emptyDescription}</p>
        </div>
      )}
    </section>
  );
}

function FeedbackRecordCard({ record }: { record: FeedbackSummary }) {
  const displayName = record.mapped_project_name ?? record.project;
  return (
    <article className="feedback-record" data-testid={`feedback-${record.project}`}>
      <div className="feedback-record-header">
        <IconTile accent="accent-amber" icon={platformIcons.feedback} size="sm" />
        <div className="feedback-record-title">
          <strong>{displayName}</strong>
          {displayName !== record.project ? <span>来源：{record.project}</span> : null}
        </div>
        {record.category_key ? <Badge className={`category-badge category-badge-${record.category_key.toLowerCase()}`}>{record.category_key}</Badge> : <Badge className="metadata-badge">待映射</Badge>}
      </div>
      <dl className="feedback-times">
        <div><dt>原人工耗时</dt><dd>{record.original_manual_time || "未填写"}</dd></div>
        <div><dt>当前处理耗时</dt><dd>{record.current_processing_time || "未填写"}</dd></div>
      </dl>
      <div className="feedback-copy"><span>业务反馈</span><p>{record.business_feedback || "未填写"}</p></div>
      <div className="feedback-copy"><span>迭代需求</span><p>{record.iteration_need || "未填写"}</p></div>
      <div className="feedback-record-meta">更新于 {record.updated_at} · {record.updated_by}</div>
    </article>
  );
}
