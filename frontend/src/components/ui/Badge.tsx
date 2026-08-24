import type { HTMLAttributes } from "react";
import { cn } from "./utils";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success";
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return <span className={cn("ui-badge", `ui-badge-${variant}`, className)} data-slot="badge" {...props} />;
}
