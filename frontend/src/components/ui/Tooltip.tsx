import type { ReactNode } from "react";

type TooltipProps = {
  children: ReactNode;
  label: string;
};

export function Tooltip({ children, label }: TooltipProps) {
  return (
    <span className="ui-tooltip" data-slot="tooltip">
      <span data-slot="tooltip-trigger">{children}</span>
      <span className="ui-tooltip-content" data-slot="tooltip-content" role="tooltip">{label}</span>
    </span>
  );
}
