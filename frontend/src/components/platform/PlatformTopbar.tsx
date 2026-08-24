import { IconBell, IconMenu2, IconSearch } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { Button, Input, Tooltip } from "../ui";

export function PlatformTopbar() {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <IconMenu2 size={18} />
        <span>中台管理平台</span>
      </div>
      <div className="topbar-actions">
        <Button asChild>
          <Link to="/projects">全域项目</Link>
        </Button>
        <label className="topbar-search">
          <IconSearch size={15} />
          <Input aria-label="搜索暂未接入" disabled placeholder="搜索暂未接入" />
        </label>
        <Tooltip label="通知暂未接入">
          <span>
            <Button aria-label="通知暂未接入" disabled size="icon"><IconBell size={16} /></Button>
          </span>
        </Tooltip>
      </div>
      <strong>Middle Platform V3</strong>
    </header>
  );
}
