import { Link } from "react-router-dom";
import type { Icon } from "@tabler/icons-react";

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
  return (
    <Link className={`quick-action ${action.accent}`} to={action.to}>
      <Icon size={18} />
      <strong>{action.title}</strong>
      <span>{action.description}</span>
    </Link>
  );
}
