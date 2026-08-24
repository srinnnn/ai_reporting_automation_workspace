import {
  IconChartBar,
  IconClock,
  IconDatabase,
  IconHome,
  IconLayoutGrid,
  IconPlayerPlay,
  IconSettings,
  type Icon,
} from "@tabler/icons-react";
import { NavLink } from "react-router-dom";

type NavigationItem = {
  icon: Icon;
  label: string;
  to: string;
};

const navItems: NavigationItem[] = [
  { to: "/", label: "首页概览", icon: IconHome },
  { to: "/workspace/ANTA", label: "品牌工作台", icon: IconLayoutGrid },
  { to: "/data-foundation", label: "数据入库中心", icon: IconDatabase },
  { to: "/tasks", label: "自动化执行", icon: IconPlayerPlay },
  { to: "/projects", label: "项目", icon: IconLayoutGrid },
  { to: "/schedule", label: "开发排期", icon: IconClock },
  { to: "/reports", label: "报表", icon: IconChartBar },
  { to: "/system", label: "系统设置", icon: IconSettings },
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
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
