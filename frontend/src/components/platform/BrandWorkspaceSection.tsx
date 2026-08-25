import { IconArrowRight } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import type { BrandSummary } from "../../types/platform";
import { Badge, Button, Card, Select } from "../ui";
import { EmptyState } from "./EmptyState";
import { platformIcons } from "./iconSemantics";

type BrandSelectorProps = {
  brands: BrandSummary[];
  selectedBrand?: BrandSummary;
  onSelect: (brandKey: string) => void;
};

type BrandWorkspaceSectionProps = BrandSelectorProps & {
};

type BrandBannerProps = {
  brand?: BrandSummary;
};

export function BrandWorkspaceSection({
  brands,
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
          <BrandBanner brand={selectedBrand ?? brands[0]} />
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
        ariaLabel="选择品牌 Workspace"
        id="brand-selector"
        className="brand-select"
        leadingIcon={platformIcons.brandWorkspace}
        options={brands.map((brand) => ({ label: brand.name, value: brand.key }))}
        value={selectedBrand?.key ?? brands[0]?.key ?? ""}
        onValueChange={onSelect}
      />
    </>
  );
}

export function BrandBanner({ brand }: BrandBannerProps) {
  const monogram = brand?.key.slice(0, 1) ?? "-";
  return (
    <section className="brand-banner" data-testid="selected-brand-banner">
      <div className="brand-monogram" aria-hidden="true">{monogram}</div>
      <div className="brand-banner-copy">
        <Badge className="metadata-badge">当前品牌</Badge>
        <strong>{brand?.name ?? "暂无数据"}</strong>
        <p>{brand?.tagline ?? "Production 默认不加载 Demo 品牌数据。"}</p>
        <em>进入单品牌开发工作台</em>
      </div>
      {brand ? (
        <Button asChild>
          <Link className="brand-enter-link" to={`/workspace/${brand.key}`}>进入 Workspace <IconArrowRight size={14} /></Link>
        </Button>
      ) : null}
    </section>
  );
}
