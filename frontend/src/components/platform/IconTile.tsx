import type { Icon } from "@tabler/icons-react";

type IconTileProps = {
  accent?: string;
  className?: string;
  icon: Icon;
  size?: "sm" | "md";
};

export function IconTile({ accent = "accent-slate", className = "", icon: Icon, size = "md" }: IconTileProps) {
  return (
    <span className={`icon-tile icon-tile-${size} ${accent} ${className}`.trim()} aria-hidden="true" data-testid="icon-tile">
      <Icon size={size === "sm" ? 16 : 20} />
    </span>
  );
}
