import { IconCalendar } from "@tabler/icons-react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BrandSelector, CategoryCard, EmptyState, MetricCard } from ".";
import { Button, Input, Tooltip } from "../ui";
import type { BrandSummary, CategorySummary } from "../../types/platform";

const brands: BrandSummary[] = [
  {
    key: "ANTA",
    name: "ANTA 安踏",
    tagline: "Brand Workspace",
    active_category_count: 2,
    categories: [],
  },
  {
    key: "BSH",
    name: "BSH 博西",
    tagline: "Brand Workspace",
    active_category_count: 2,
    categories: [],
  },
];

const p4Category: CategorySummary = {
  key: "P4",
  name: "复查",
  capability_count: 0,
  status: "NOT_CONNECTED",
  capabilities: [],
};

describe("platform homepage components", () => {
  afterEach(() => {
    cleanup();
  });

  it("BrandSelector emits the selected brand key", async () => {
    const onSelect = vi.fn();
    render(<BrandSelector brands={brands} selectedBrand={brands[0]} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole("combobox", { name: "选择品牌 Workspace" }));
    await userEvent.click(screen.getByRole("option", { name: "BSH 博西" }));

    expect(onSelect).toHaveBeenCalledWith("BSH");
  });

  it("Button composes navigation with asChild", () => {
    render(
      <MemoryRouter>
        <Button asChild>
          <Link to="/tasks">新建任务</Link>
        </Button>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "新建任务" })).toHaveAttribute("href", "/tasks");
  });

  it("Tooltip exposes accessible content on hover", async () => {
    render(
      <Tooltip label="通知暂未接入">
        <button type="button">通知</button>
      </Tooltip>,
    );

    await userEvent.hover(screen.getByRole("button", { name: "通知" }));

    expect(await screen.findByRole("tooltip")).toHaveTextContent("通知暂未接入");
  });

  it("Input supports disabled search placeholder state", () => {
    render(<Input aria-label="搜索暂未接入" disabled placeholder="搜索暂未接入" />);

    expect(screen.getByRole("textbox", { name: "搜索暂未接入" })).toBeDisabled();
    expect(screen.getByPlaceholderText("搜索暂未接入")).toBeInTheDocument();
  });

  it("MetricCard renders non-numeric feedback state", () => {
    render(
      <MetricCard
        metric={{
          accent: "accent-amber",
          icon: IconCalendar,
          label: "反馈",
          note: "暂无数据源",
          testId: "kpi-feedback",
          value: "未接入",
        }}
      />,
    );

    expect(screen.getByTestId("kpi-feedback")).toHaveTextContent("反馈");
    expect(screen.getByTestId("kpi-feedback")).toHaveTextContent("未接入");
    expect(screen.getByTestId("kpi-feedback")).not.toHaveTextContent("0");
  });

  it("CategoryCard keeps brand and P-category route without exposing capabilities", () => {
    render(
      <MemoryRouter>
        <CategoryCard brand={brands[1]} category={p4Category} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /P4/ })).toHaveAttribute("href", "/workspace/BSH/P4");
    expect(screen.getByText("暂无接入能力")).toBeInTheDocument();
  });

  it("EmptyState renders explicit empty copy", () => {
    render(<EmptyState text="当前品牌暂无项目数据" />);

    expect(screen.getByText("当前品牌暂无项目数据")).toBeInTheDocument();
  });
});
