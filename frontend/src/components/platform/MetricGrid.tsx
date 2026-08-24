import type { Icon } from "@tabler/icons-react";

type Metric = {
  accent: string;
  icon: Icon;
  label: string;
  note: string;
  testId: string;
  value: string | number;
};

export function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="kpi-grid" data-testid="selected-brand-kpi" data-homepage-module="true" data-module="selected-brand-kpi">
      {metrics.map((metric) => <MetricCard key={metric.testId} metric={metric} />)}
    </section>
  );
}

export function MetricCard({ metric }: { metric: Metric }) {
  const Icon = metric.icon;
  return (
    <article className={`kpi-card ${metric.accent}`} data-testid={metric.testId}>
      <Icon size={18} />
      <span>{metric.label}</span>
      <strong>{metric.value}</strong>
      <em>{metric.note}</em>
    </article>
  );
}
