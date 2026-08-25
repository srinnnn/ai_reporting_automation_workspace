import { IconFilter } from "@tabler/icons-react";
import type { BrandSummary, ProjectSummary } from "../../types/platform";
import { Select } from "../ui";
import { platformIcons } from "./iconSemantics";

export type GlobalFilters = {
  brandKey: string;
  categoryKey: string;
  projectKey: string;
  status: string;
};

type GlobalFilterBarProps = {
  brands: BrandSummary[];
  filters: GlobalFilters;
  onChange: (filters: GlobalFilters) => void;
  projects: ProjectSummary[];
};

const allValue = "ALL";
const categoryOptions = [
  { label: "全部分类", value: allValue },
  { label: "P1 数据提效", value: "P1" },
  { label: "P2 内容提效", value: "P2" },
  { label: "P3 配置提效", value: "P3" },
  { label: "P4 复查", value: "P4" },
];

export function GlobalFilterBar({ brands, filters, onChange, projects }: GlobalFilterBarProps) {
  const projectOptions = [
    { label: "全部项目", value: allValue },
    ...projects.map((project) => ({ label: project.name, value: project.key })),
  ];
  const brandOptions = [
    { label: "全部品牌", value: allValue },
    ...brands.map((brand) => ({ label: brand.name, value: brand.key })),
  ];
  const statusOptions = [
    { label: "全部状态", value: allValue },
    ...Array.from(new Set(projects.map((project) => project.status))).map((status) => ({ label: status, value: status })),
  ];

  return (
    <section className="filter-bar" data-testid="global-filters" data-homepage-module="true" data-module="global-filters">
      <span><IconFilter size={16} /> 全局筛选</span>
      <Select ariaLabel="项目" className="filter-select" leadingIcon={platformIcons.project} options={projectOptions} value={filters.projectKey} onValueChange={(projectKey) => onChange({ ...filters, projectKey })} />
      <Select ariaLabel="品牌" className="filter-select" leadingIcon={platformIcons.brandWorkspace} options={brandOptions} value={filters.brandKey} onValueChange={(brandKey) => onChange({ ...filters, brandKey })} />
      <Select ariaLabel="P分类" className="filter-select" leadingIcon={platformIcons.category} options={categoryOptions} value={filters.categoryKey} onValueChange={(categoryKey) => onChange({ ...filters, categoryKey })} />
      <Select ariaLabel="状态" className="filter-select" leadingIcon={platformIcons.activity} options={statusOptions} value={filters.status} onValueChange={(status) => onChange({ ...filters, status })} />
    </section>
  );
}
