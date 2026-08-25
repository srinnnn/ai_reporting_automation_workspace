import type { Icon } from "@tabler/icons-react";
import { IconTile } from "./IconTile";

type Metric = {
  accent: string;
  icon: Icon;
  label: string;
  note: string;
  testId: string;
  value: string | number;
};

type MetricGridProps = {
  dataModule?: string;
  homepageModule?: boolean;
  metrics: Metric[];
  testId?: string;
};

export function MetricGrid({ dataModule = "global-kpi", homepageModule = true, metrics, testId = "global-kpi" }: MetricGridProps) {
  return (
    <section className="kpi-grid" data-testid={testId} {...(homepageModule ? { "data-homepage-module": "true" } : {})} data-module={dataModule}>
      {metrics.map((metric) => <MetricCard key={metric.testId} metric={metric} />)}
    </section>
  );
}

export function MetricCard({ metric }: { metric: Metric }) {
  const Icon = metric.icon;
  return (
    <article className={`kpi-card ${metric.accent}`} data-testid={metric.testId}>
      <IconTile accent={metric.accent} icon={Icon} />
      <span>{metric.label}</span>
      <strong>{metric.value}</strong>
      <em>{metric.note}</em>
    </article>
  );
}
