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
      key: "ECCO",
      name: "ECCO",
      tagline: "Brand Workspace",
      active_category_count: 1,
      categories: [],
    },
  ],
  projects: [],
  kpis: { brand_count: 2, connected_project_count: 0 },
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

describe("HomePage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders locked homepage controls and one selected-brand banner", async () => {
    renderHome();

    expect(await screen.findByRole("heading", { name: "中台全局首页" })).toBeInTheDocument();
    expect(screen.getByTestId("global-filters")).toHaveTextContent("项目品牌优先级状态");
    expect(await screen.findByRole("combobox", { name: "品牌" })).toHaveValue("ANTA");
    expect(screen.getAllByTestId("selected-brand-banner")).toHaveLength(1);
    expect(screen.queryByText("进入工作台")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /进入 Brand Workspace/ })).toHaveAttribute("href", "/workspace/ANTA");
  });

  it("updates the selected-brand banner from the dropdown", async () => {
    renderHome();

    await userEvent.selectOptions(await screen.findByRole("combobox", { name: "品牌" }), "ECCO");

    expect(screen.getByTestId("selected-brand-banner")).toHaveTextContent("ECCO");
    expect(screen.getByRole("link", { name: /进入 Brand Workspace/ })).toHaveAttribute("href", "/workspace/ECCO");
  });
});
