import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { HomePage } from "./HomePage";

function renderHome() {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({ brands: [], projects: [], kpis: { brand_count: 0, connected_project_count: 0 } }),
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
  it("renders baseline module order with production empty state", async () => {
    renderHome();

    expect(await screen.findByText("中台全局首页")).toBeInTheDocument();
    expect(screen.getByText("品牌 Workspace 入口")).toBeInTheDocument();
    expect(screen.getByText("当前品牌")).toBeInTheDocument();
    expect(screen.getByText("能力分类")).toBeInTheDocument();
    expect(screen.getAllByText("已接项目").length).toBeGreaterThan(0);
    expect(screen.getByText("已开发反馈汇总")).toBeInTheDocument();
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
  });
});
