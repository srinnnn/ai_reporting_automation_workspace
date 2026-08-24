import { IconArrowRight } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { BrandSummary, CategorySummary } from "../../types/platform";

type CategoryGridProps = {
  brand?: BrandSummary;
  categories: CategorySummary[];
};

export function CategoryGrid({ brand, categories }: CategoryGridProps) {
  return (
    <section className="panel category-panel" data-testid="p1-p4-category-grid" data-homepage-module="true" data-module="p1-p4">
      <div className="section-title">
        <h2>P1-P4 分级入口</h2>
        <span>仅展示入口，不展开全部能力</span>
      </div>
      <div className="category-grid">
        {categories.map((category) => <CategoryCard brand={brand} category={category} key={category.key} />)}
      </div>
    </section>
  );
}

export function CategoryCard({ brand, category }: { brand?: BrandSummary; category: CategorySummary }) {
  return (
    <Link
      className={`category-card category-${category.key.toLowerCase()}`}
      data-testid={`category-${category.key}`}
      to={brand ? `/workspace/${brand.key}/${category.key}` : "/workspace/UNKNOWN"}
    >
      <strong>{category.key}</strong>
      <span>{category.name}</span>
      <em>{category.capability_count > 0 ? `${category.capability_count} 个能力` : "暂无接入能力"}</em>
      <small>进入分级 <IconArrowRight size={13} /></small>
    </Link>
  );
}
