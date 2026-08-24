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

function renderHome() {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => dashboard,
  })));
  const router = createMemoryRouter([{ path: "/", element: <HomePage /> }]);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

async function selectBrand(label: string) {
  await userEvent.click(await screen.findByRole("combobox", { name: "品牌" }));
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
    expect(screen.getByTestId("global-filters")).toHaveTextContent("项目品牌优先级状态");
    expect(await screen.findByRole("combobox", { name: "品牌" })).toHaveTextContent("ANTA 安踏");
    expect(screen.getAllByTestId("selected-brand-banner")).toHaveLength(1);
    expect(screen.getByTestId("kpi-active-categories")).toHaveTextContent("2");
    expect(screen.getByTestId("kpi-connected-projects")).toHaveTextContent("2");
    expect(screen.getByTestId("project-anta_reporting")).toBeInTheDocument();
    expect(screen.getByTestId("project-anta_retail")).toBeInTheDocument();
    expect(screen.queryByTestId("project-bosch_sms")).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/ANTA");
  });

  it("updates brand-scoped KPIs, category counts, projects, and feedback from the dropdown", async () => {
    renderHome();

    await selectBrand("BSH 博西");

    expect(screen.getByTestId("selected-brand-banner")).toHaveTextContent("BSH 博西");
    expect(screen.getByTestId("kpi-active-categories")).toHaveTextContent("2");
    expect(screen.getByTestId("kpi-connected-projects")).toHaveTextContent("2");
    expect(screen.getByTestId("category-P1")).toHaveTextContent("1 个能力");
    expect(screen.getByTestId("category-P3")).toHaveTextContent("暂无接入能力");
    expect(screen.getByTestId("category-P4")).toHaveTextContent("1 个能力");
    expect(screen.getByTestId("project-bosch_sms")).toBeInTheDocument();
    expect(screen.getByTestId("project-bosch_sms_review")).toBeInTheDocument();
    expect(screen.queryByTestId("project-anta_reporting")).not.toBeInTheDocument();
    expect(screen.getByText("当前品牌暂无反馈记录")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/BSH");
  });
});
