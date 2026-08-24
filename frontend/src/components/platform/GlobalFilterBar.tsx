import { IconFilter } from "@tabler/icons-react";
import { Button } from "../ui";

const filterLabels = ["项目", "品牌", "优先级", "状态"];

export function GlobalFilterBar() {
  return (
    <section className="filter-bar" data-testid="global-filters" data-homepage-module="true" data-module="global-filters">
      <span><IconFilter size={16} /> 全局筛选</span>
      {filterLabels.map((label) => <Button key={label}>{label}</Button>)}
    </section>
  );
}
