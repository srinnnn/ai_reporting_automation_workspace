import type { Icon } from "@tabler/icons-react";
import { NavLink } from "react-router-dom";
import { platformIcons } from "./iconSemantics";

type NavigationItem = {
  icon: Icon;
  label: string;
  to: string;
};

const navItems: NavigationItem[] = [
  { to: "/", label: "首页概览", icon: platformIcons.home },
  { to: "/workspace/ANTA", label: "品牌工作台", icon: platformIcons.brandWorkspace },
  { to: "/data-foundation", label: "数据入库中心", icon: platformIcons.data },
  { to: "/tasks", label: "自动化执行", icon: platformIcons.automation },
  { to: "/projects", label: "项目", icon: platformIcons.project },
  { to: "/schedule", label: "开发排期", icon: platformIcons.schedule },
  { to: "/reports", label: "报表", icon: platformIcons.report },
  { to: "/system", label: "系统设置", icon: platformIcons.settings },
];

export function PlatformSidebar() {
  return (
    <aside className="sidebar">
      <div className="brand-mark">
        <div className="cube" />
        <div>
          <strong>运营一组</strong>
          <span>AI 自动化中台</span>
        </div>
      </div>
      <nav>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              <span className="nav-icon" data-testid="nav-icon"><Icon size={18} /></span>
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
