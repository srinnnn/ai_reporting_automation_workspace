import * as RadixTooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

type TooltipProps = {
  children: ReactNode;
  label: string;
};

export function Tooltip({ children, label }: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={180}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content className="ui-tooltip-content" data-slot="tooltip-content" role="tooltip" sideOffset={6}>
            {label}
            <RadixTooltip.Arrow className="ui-tooltip-arrow" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
