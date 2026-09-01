import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "./HomePage";

const dashboard = {
  brands: [
    {
      key: "ANTA",
      name: "ANTA 安踏",
      tagline: "Brand Workspace",
      active_category_count: 2,
      categories: [
        { key: "P1", name: "数据提效", capability_count: 1, status: "CONNECTED", capabilities: [] },
        { key: "P2", name: "内容提效", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
        { key: "P3", name: "配置提效", capability_count: 1, status: "CONNECTED", capabilities: [] },
        { key: "P4", name: "复查", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
      ],
    },
    {
      key: "BSH",
      name: "BSH 博西",
      tagline: "Brand Workspace",
      active_category_count: 2,
      categories: [
        { key: "P1", name: "数据提效", capability_count: 1, status: "CONNECTED", capabilities: [] },
        { key: "P2", name: "内容提效", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
        { key: "P3", name: "配置提效", capability_count: 0, status: "NOT_CONNECTED", capabilities: [] },
        { key: "P4", name: "复查", capability_count: 1, status: "CONNECTED", capabilities: [] },
      ],
    },
  ],
  projects: [
    { key: "anta_reporting", name: "安踏周报/月报", brand_key: "ANTA", category_key: "P1", status: "CONNECTED" },
    { key: "anta_retail", name: "安踏即时零售", brand_key: "ANTA", category_key: "P3", status: "CONNECTED" },
    { key: "bosch_sms", name: "博西短彩信数据处理", brand_key: "BSH", category_key: "P1", status: "CONNECTED" },
    { key: "bosch_sms_review", name: "博世/西门子短彩信规划复核", brand_key: "BSH", category_key: "P4", status: "CONNECTED" },
  ],
  kpis: { brand_count: 2, connected_project_count: 4 },
};

const feedback = [
  { project: "安踏周报/月报", mapped_project_key: "anta_reporting", mapped_project_name: "安踏周报/月报", brand_key: "ANTA", category_key: "P1", status: "CONNECTED", original_manual_time: "2小时", current_processing_time: "1小时", business_feedback: "ANTA P1反馈", iteration_need: "ANTA P1迭代", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
  { project: "P3-即时零售-安踏", mapped_project_key: "anta_retail", mapped_project_name: "安踏即时零售", brand_key: "ANTA", category_key: "P3", status: "CONNECTED", original_manual_time: "4小时", current_processing_time: "1小时", business_feedback: "ANTA P3反馈", iteration_need: "ANTA P3迭代", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
  { project: "博西短彩信数据处理", mapped_project_key: "bosch_sms", mapped_project_name: "博西短彩信数据处理", brand_key: "BSH", category_key: "P1", status: "CONNECTED", original_manual_time: "3小时", current_processing_time: "1小时", business_feedback: "BSH反馈", iteration_need: "BSH迭代", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
  { project: "P1-短彩信数据处理-CK", mapped_project_key: null, mapped_project_name: null, brand_key: null, category_key: null, status: "UNMAPPED", original_manual_time: "3小时", current_processing_time: "1小时", business_feedback: "待映射反馈", iteration_need: "待映射迭代", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
];

function renderHome() {
  vi.stubGlobal("fetch", vi.fn(async (input: string | URL | Request) => ({
    ok: true,
    json: async () => String(input).includes("/api/v1/feedback") ? feedback : dashboard,
  })));
  const router = createMemoryRouter([{ path: "/", element: <HomePage /> }]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

async function selectOption(controlName: string, label: string) {
  await userEvent.click(await screen.findByRole("combobox", { name: controlName }));
  await userEvent.click(await screen.findByRole("option", { name: label }));
}

describe("HomePage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders locked homepage controls and one selected-brand banner", async () => {
    renderHome();

    expect(await screen.findByRole("heading", { name: "中台全局首页" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "项目" })).toHaveTextContent("全部项目");
    expect(screen.getByRole("combobox", { name: "品牌" })).toHaveTextContent("全部品牌");
    expect(screen.getByRole("combobox", { name: "P分类" })).toHaveTextContent("全部分类");
    expect(screen.getByRole("combobox", { name: "状态" })).toHaveTextContent("全部状态");
    expect(await screen.findByRole("combobox", { name: "选择品牌 Workspace" })).toHaveTextContent("ANTA 安踏");
    expect(screen.getAllByTestId("selected-brand-banner")).toHaveLength(1);
    expect(screen.getByTestId("kpi-brand-count")).toHaveTextContent("2");
    expect(screen.getByTestId("kpi-active-categories")).toHaveTextContent("3");
    expect(screen.getByTestId("kpi-connected-projects")).toHaveTextContent("4");
    expect(screen.getByTestId("project-anta_reporting")).toBeInTheDocument();
    expect(screen.getByTestId("project-anta_retail")).toBeInTheDocument();
    expect(screen.getByTestId("project-bosch_sms")).toBeInTheDocument();
    expect(screen.getByTestId("project-bosch_sms_review")).toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/ANTA");
    expect(screen.getByTestId("kpi-feedback")).toHaveTextContent("4");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("全部品牌 / 4 条");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("ANTA P1反馈");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("待映射反馈");
  });

  it("keeps global dashboard data unchanged when the Workspace Entry selector changes", async () => {
    renderHome();

    await selectOption("选择品牌 Workspace", "BSH 博西");

    expect(screen.getByTestId("selected-brand-banner")).toHaveTextContent("BSH 博西");
    expect(screen.getByTestId("kpi-brand-count")).toHaveTextContent("2");
    expect(screen.getByTestId("kpi-active-categories")).toHaveTextContent("3");
    expect(screen.getByTestId("kpi-connected-projects")).toHaveTextContent("4");
    expect(screen.getByTestId("category-P1")).toHaveTextContent("2 个能力");
    expect(screen.getByTestId("category-P3")).toHaveTextContent("1 个能力");
    expect(screen.getByTestId("category-P4")).toHaveTextContent("1 个能力");
    expect(screen.getByTestId("project-anta_reporting")).toBeInTheDocument();
    expect(screen.getByTestId("project-anta_retail")).toBeInTheDocument();
    expect(screen.getByTestId("project-bosch_sms")).toBeInTheDocument();
    expect(screen.getByTestId("project-bosch_sms_review")).toBeInTheDocument();
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("全部品牌 / 4 条");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("待映射反馈");
    expect(screen.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/BSH");
  });

  it("scopes global dashboard data only from the Global Brand Filter", async () => {
    renderHome();

    await selectOption("选择品牌 Workspace", "BSH 博西");
    await selectOption("品牌", "ANTA 安踏");

    expect(screen.getByTestId("selected-brand-banner")).toHaveTextContent("BSH 博西");
    expect(screen.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/BSH");
    expect(screen.getByTestId("kpi-brand-count")).toHaveTextContent("1");
    expect(screen.getByTestId("kpi-active-categories")).toHaveTextContent("2");
    expect(screen.getByTestId("kpi-connected-projects")).toHaveTextContent("2");
    expect(screen.getByTestId("category-P1")).toHaveTextContent("1 个能力");
    expect(screen.getByTestId("category-P2")).toHaveTextContent("暂无接入能力");
    expect(screen.getByTestId("category-P3")).toHaveTextContent("1 个能力");
    expect(screen.getByTestId("category-P4")).toHaveTextContent("暂无接入能力");
    expect(screen.getByTestId("project-anta_reporting")).toBeInTheDocument();
    expect(screen.getByTestId("project-anta_retail")).toBeInTheDocument();
    expect(screen.queryByTestId("project-bosch_sms")).not.toBeInTheDocument();
    expect(screen.queryByTestId("project-bosch_sms_review")).not.toBeInTheDocument();
    expect(screen.getByTestId("kpi-feedback")).toHaveTextContent("2");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("ANTA 安踏 / 2 条");
    expect(screen.getByTestId("developed-feedback")).toHaveTextContent("ANTA P1反馈");
    expect(screen.getByTestId("developed-feedback")).not.toHaveTextContent("BSH反馈");
    expect(screen.getByTestId("developed-feedback")).not.toHaveTextContent("待映射反馈");
  });
});
