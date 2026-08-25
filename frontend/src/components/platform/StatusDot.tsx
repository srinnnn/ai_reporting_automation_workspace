type StatusDotProps = {
  status: string;
};

export function StatusDot({ status }: StatusDotProps) {
  const tone = statusTone(status);
  return (
    <span className={`status-dot status-dot-${tone}`} data-testid="status-dot">
      <span aria-hidden="true" />
      <em>{status}</em>
    </span>
  );
}

function statusTone(status: string) {
  const normalized = status.trim().toUpperCase();
  if (normalized.includes("REVIEW")) return "review";
  if (normalized.includes("CONNECTED") || normalized.includes("COMPLETE") || normalized.includes("READY")) return "success";
  if (normalized.includes("DEVELOP") || normalized.includes("RUNNING") || normalized.includes("PROGRESS")) return "progress";
  if (normalized.includes("BLOCK") || normalized.includes("ERROR") || normalized.includes("FAIL")) return "blocked";
  return "neutral";
}
