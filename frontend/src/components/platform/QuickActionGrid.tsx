import { Link } from "react-router-dom";
import type { Icon } from "@tabler/icons-react";
import { IconTile } from "./IconTile";
import { platformIcons } from "./iconSemantics";

type QuickAction = {
  accent: string;
  description: string;
  icon: Icon;
  title: string;
  to: string;
};

export function QuickActionGrid({ actions }: { actions: QuickAction[] }) {
  return (
    <section className="quick-nav" data-testid="quick-navigation" data-homepage-module="true" data-module="quick-navigation">
      {actions.map((action) => <QuickActionCard action={action} key={action.to} />)}
    </section>
  );
}

export function QuickActionCard({ action }: { action: QuickAction }) {
  const Icon = action.icon;
  const ActionIcon = platformIcons.action;
  return (
    <Link className={`quick-action ${action.accent}`} to={action.to}>
      <IconTile accent={action.accent} icon={Icon} />
      <strong>{action.title}</strong>
      <span>{action.description}</span>
      <ActionIcon className="quick-action-arrow" size={15} />
    </Link>
  );
}
