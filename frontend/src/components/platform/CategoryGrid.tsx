import { IconArrowRight } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { BrandSummary, CategorySummary } from "../../types/platform";

type CategoryGridProps = {
  brand?: BrandSummary;
  categories: CategorySummary[];
  dataModule?: string;
  homepageModule?: boolean;
  subtitle?: string;
  title?: string;
};

export function CategoryGrid({
  brand,
  categories,
  dataModule = "global-p1-p4",
  homepageModule = true,
  subtitle = "汇总当前全局筛选范围内的 P1-P4 项目能力",
  title = "P1-P4 开发概览",
}: CategoryGridProps) {
  return (
    <section className="panel category-panel" data-testid="p1-p4-category-grid" {...(homepageModule ? { "data-homepage-module": "true" } : {})} data-module={dataModule}>
      <div className="section-title">
        <h2>{title}</h2>
        <span>{subtitle}</span>
      </div>
      <div className="category-grid">
        {categories.map((category) => <CategoryCard brand={brand} category={category} key={category.key} />)}
      </div>
    </section>
  );
}

export function CategoryCard({ brand, category }: { brand?: BrandSummary; category: CategorySummary }) {
  const content = (
    <>
      <strong>{category.key}</strong>
      <span>{category.name}</span>
      <em>{category.capability_count > 0 ? `${category.capability_count} 个能力` : "暂无接入能力"}</em>
      <small>{brand ? "进入分级" : "全局概览"} <IconArrowRight size={13} /></small>
    </>
  );

  if (!brand) {
    return (
      <article className={`category-card category-${category.key.toLowerCase()}`} data-testid={`category-${category.key}`}>
        {content}
      </article>
    );
  }

  return (
    <Link
      className={`category-card category-${category.key.toLowerCase()}`}
      data-testid={`category-${category.key}`}
      to={`/workspace/${brand.key}/${category.key}`}
    >
      {content}
    </Link>
  );
}
