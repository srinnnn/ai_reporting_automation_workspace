import { IconCalendar } from "@tabler/icons-react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BrandSelector,
  CategoryCard,
  EmptyState,
  FeedbackPanel,
  MetricCard,
  PlatformSidebar,
  ProjectRow,
  QuickActionGrid,
  StatusDot,
} from ".";
import { Button, Input, Tooltip } from "../ui";
import { platformIcons } from "./iconSemantics";
import type { BrandSummary, CategorySummary, FeedbackSummary, ProjectSummary } from "../../types/platform";

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

const projects: ProjectSummary[] = [
  { key: "anta_reporting", name: "安踏周报/月报", brand_key: "ANTA", category_key: "P1", status: "CONNECTED" },
];

const feedback: FeedbackSummary[] = [
  {
    project: "P3-即时零售-安踏",
    mapped_project_key: "anta_retail",
    mapped_project_name: "安踏即时零售",
    brand_key: "ANTA",
    category_key: "P3",
    status: "CONNECTED",
    original_manual_time: "74小时",
    current_processing_time: "1小时",
    business_feedback: "运行稳定",
    iteration_need: "增加批量处理",
    updated_by: "admin",
    updated_at: "2026-08-26 10:00:00",
  },
];

const quickActions = [
  { to: "/data-foundation", title: "数据入库", description: "进入数据入库中心", icon: platformIcons.data, accent: "accent-slate" },
  { to: "/tasks", title: "自动化执行", description: "运行已接入自动化任务", icon: platformIcons.automation, accent: "accent-sage" },
  { to: "/reports", title: "查看报表", description: "查看数据与结果", icon: platformIcons.report, accent: "accent-lavender" },
  { to: "/schedule", title: "开发排期", description: "查看项目开发状态", icon: platformIcons.schedule, accent: "accent-amber" },
];

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
    expect(screen.getByTestId("icon-tile")).toBeInTheDocument();
  });

  it("CategoryCard keeps brand and P-category route without exposing capabilities", () => {
    render(
      <MemoryRouter>
        <CategoryCard brand={brands[1]} category={p4Category} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /P4/ })).toHaveAttribute("href", "/workspace/BSH/P4");
    expect(screen.getByText("暂无接入能力")).toBeInTheDocument();
    expect(screen.getByText("P4")).toHaveAttribute("data-slot", "badge");
    expect(screen.getByTestId("icon-tile")).toBeInTheDocument();
  });

  it("PlatformSidebar renders semantic icon containers for primary navigation", () => {
    render(
      <MemoryRouter>
        <PlatformSidebar />
      </MemoryRouter>,
    );

    expect(screen.getAllByTestId("nav-icon")).toHaveLength(8);
    expect(screen.getByRole("link", { name: "首页概览" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "品牌工作台" })).toBeInTheDocument();
  });

  it("ProjectRow renders category badge, status text, and action affordance", () => {
    render(
      <MemoryRouter>
        <ProjectRow project={projects[0]} />
      </MemoryRouter>,
    );

    expect(screen.getByText("P1")).toHaveAttribute("data-slot", "badge");
    expect(screen.getByTestId("status-dot")).toHaveTextContent("CONNECTED");
    expect(screen.getByRole("link", { name: /安踏周报\/月报/ })).toHaveAttribute("href", "/projects/anta_reporting");
  });

  it.each([
    ["READY_FOR_REVIEW", "review"],
    ["CONNECTED", "success"],
    ["IN_DEVELOPMENT", "progress"],
    ["BLOCKED", "blocked"],
    ["AVAILABLE", "success"],
    ["UNAVAILABLE", "blocked"],
  ])("StatusDot maps %s to %s tone", (status, tone) => {
    render(<StatusDot status={status} />);

    expect(screen.getByTestId("status-dot")).toHaveClass(`status-dot-${tone}`);
    expect(screen.getByTestId("status-dot")).toHaveTextContent(status);
  });

  it("FeedbackPanel empty state includes icon and truthful text", () => {
    render(<FeedbackPanel emptyTitle="当前暂无已接入的开发反馈数据" />);

    expect(screen.getByTestId("icon-tile")).toBeInTheDocument();
    expect(screen.getByText("当前暂无已接入的开发反馈数据")).toBeInTheDocument();
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("0 条");
  });

  it("FeedbackPanel renders existing feedback fields", () => {
    render(<FeedbackPanel records={feedback} />);

    expect(screen.getByRole("region", { name: "反馈记录横向列表" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("全部品牌 / 1 条");
    expect(screen.getByText("安踏即时零售")).toBeInTheDocument();
    expect(screen.getByText("来源：P3-即时零售-安踏")).toBeInTheDocument();
    expect(screen.getByText("74小时")).toBeInTheDocument();
    expect(screen.getByText("1小时")).toBeInTheDocument();
    expect(screen.getByText("运行稳定")).toBeInTheDocument();
    expect(screen.getByText("增加批量处理")).toBeInTheDocument();
    expect(screen.getByText(/admin/)).toBeInTheDocument();
  });

  it("QuickActionGrid renders four approved icon-assisted actions", () => {
    render(
      <MemoryRouter>
        <QuickActionGrid actions={quickActions} />
      </MemoryRouter>,
    );

    expect(screen.getAllByTestId("icon-tile")).toHaveLength(4);
    expect(screen.getByRole("link", { name: /数据入库/ })).toHaveAttribute("href", "/data-foundation");
    expect(screen.getByRole("link", { name: /开发排期/ })).toHaveAttribute("href", "/schedule");
  });

  it("EmptyState renders explicit empty copy", () => {
    render(<EmptyState text="当前品牌暂无项目数据" />);

    expect(screen.getByText("当前品牌暂无项目数据")).toBeInTheDocument();
  });
});
