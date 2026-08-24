import { IconCalendar, IconPlus } from "@tabler/icons-react";
import { Button } from "../ui";

export function PageHeader() {
  return (
    <section className="page-header" data-homepage-module="true" data-module="page-header">
      <div>
        <p className="eyebrow">品牌工作台 / Brand Workspace Overview</p>
        <h1>中台全局首页</h1>
        <p>首页展示核心概览与分类入口，不展开全部能力。</p>
      </div>
      <div className="header-actions">
        <Button><IconCalendar size={16} /> 今天</Button>
        <Button variant="primary"><IconPlus size={16} /> 新建任务</Button>
      </div>
    </section>
  );
}
