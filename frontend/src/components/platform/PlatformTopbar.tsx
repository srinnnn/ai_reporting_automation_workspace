import { IconBell, IconMenu2, IconSearch } from "@tabler/icons-react";
import { Button, Tooltip } from "../ui";

export function PlatformTopbar() {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <IconMenu2 size={18} />
        <span>中台管理平台</span>
      </div>
      <div className="topbar-actions">
        <Button>全域项目</Button>
        <label className="topbar-search">
          <IconSearch size={15} />
          <input placeholder="搜索项目、品牌或功能..." />
        </label>
        <Tooltip label="通知">
          <Button aria-label="通知" size="icon"><IconBell size={16} /></Button>
        </Tooltip>
      </div>
      <strong>Middle Platform V3</strong>
    </header>
  );
}
