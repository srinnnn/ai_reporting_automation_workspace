import { IconArrowRight } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { BrandSummary } from "../../types/platform";
import { Button, Card, Select } from "../ui";
import { EmptyState } from "./EmptyState";

type BrandSelectorProps = {
  brands: BrandSummary[];
  selectedBrand?: BrandSummary;
  onSelect: (brandKey: string) => void;
};

type BrandWorkspaceSectionProps = BrandSelectorProps & {
  activeCategoryCount: number;
  capabilityCount: number;
};

type BrandBannerProps = {
  activeCategoryCount: number;
  brand?: BrandSummary;
  capabilityCount: number;
};

export function BrandWorkspaceSection({
  activeCategoryCount,
  brands,
  capabilityCount,
  onSelect,
  selectedBrand,
}: BrandWorkspaceSectionProps) {
  return (
    <Card className="panel brand-workspace-panel" data-testid="brand-workspace-entry" data-homepage-module="true" data-module="brand-workspace">
      <div className="section-title">
        <h2>品牌 Workspace 入口</h2>
        <span>{brands.length || 0} 个品牌</span>
      </div>
      {brands.length ? (
        <>
          <BrandSelector brands={brands} selectedBrand={selectedBrand} onSelect={onSelect} />
          <BrandBanner
            activeCategoryCount={activeCategoryCount}
            brand={selectedBrand ?? brands[0]}
            capabilityCount={capabilityCount}
          />
        </>
      ) : <EmptyState text="暂无品牌数据" />}
    </Card>
  );
}

export function BrandSelector({ brands, onSelect, selectedBrand }: BrandSelectorProps) {
  return (
    <>
      <label className="brand-select-label" htmlFor="brand-selector">品牌</label>
      <Select
        id="brand-selector"
        className="brand-select"
        value={selectedBrand?.key ?? brands[0]?.key ?? ""}
        onChange={(event) => onSelect(event.target.value)}
      >
        {brands.map((brand) => <option value={brand.key} key={brand.key}>{brand.name}</option>)}
      </Select>
    </>
  );
}

export function BrandBanner({ activeCategoryCount, brand, capabilityCount }: BrandBannerProps) {
  const monogram = brand?.key.slice(0, 1) ?? "-";
  return (
    <section className="brand-banner" data-testid="selected-brand-banner">
      <div className="brand-monogram" aria-hidden="true">{monogram}</div>
      <div className="brand-banner-copy">
        <span>当前品牌</span>
        <strong>{brand?.name ?? "暂无数据"}</strong>
        <p>{brand?.tagline ?? "Production 默认不加载 Demo 品牌数据。"}</p>
        <em>{activeCategoryCount} 个分类 · {capabilityCount} 个能力</em>
      </div>
      <div className="brand-banner-meta">
        <span>已接分类</span>
        <strong>{activeCategoryCount}</strong>
      </div>
      {brand ? (
        <Button asChild>
          <Link className="brand-enter-link" to={`/workspace/${brand.key}`}>进入 Workspace <IconArrowRight size={14} /></Link>
        </Button>
      ) : null}
    </section>
  );
}
