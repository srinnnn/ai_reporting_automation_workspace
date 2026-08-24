import { IconCalendar, IconPlus } from "@tabler/icons-react";
import { Link } from "react-router-dom";
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
        <time className="date-chip" dateTime="today"><IconCalendar size={16} /> 今天</time>
        <Button asChild variant="primary">
          <Link to="/tasks"><IconPlus size={16} /> 新建任务</Link>
        </Button>
      </div>
    </section>
  );
}
