import {
  IconArchive,
  IconBell,
  IconChartBar,
  IconClock,
  IconDatabase,
  IconHome,
  IconLayoutGrid,
  IconMenu2,
  IconPlayerPlay,
  IconSearch,
  IconSettings,
} from "@tabler/icons-react";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "首页概览", icon: IconHome },
  { to: "/workspace/ANTA", label: "品牌工作台", icon: IconLayoutGrid },
  { to: "/data-foundation", label: "数据入库中心", icon: IconDatabase },
  { to: "/tasks", label: "自动化执行", icon: IconPlayerPlay },
  { to: "/projects", label: "投递资料", icon: IconArchive },
  { to: "/schedule", label: "最近处理记录", icon: IconClock },
  { to: "/reports", label: "数据分析报表", icon: IconChartBar },
  { to: "/system", label: "系统设置", icon: IconSettings },
];

export function AppLayout() {
  return (
    <div className="shell">
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
      <main className="main">
        <header className="topbar">
          <div className="topbar-title">
            <IconMenu2 size={18} />
            <span>中台管理平台</span>
          </div>
          <div className="topbar-actions">
            <button>全域项目</button>
            <label className="topbar-search">
              <IconSearch size={15} />
              <input placeholder="搜索项目、品牌或功能..." />
            </label>
            <button aria-label="通知"><IconBell size={16} /></button>
          </div>
          <strong>Middle Platform V3</strong>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
