import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ModulePage } from "./ModulePage";

describe("ModulePage projects", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders registered projects instead of the placeholder", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => [
        {
          key: "private_data_local_center",
          name: "私域数据采集中心",
          brand_key: "ANTA",
          category_key: "P1",
          status: "CONFIGURED",
        },
      ],
    })));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ModulePage title="项目管理" moduleKey="projects" />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByTestId("project-private_data_local_center")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /私域数据采集中心/ })).toHaveAttribute(
      "href",
      "/projects/private_data_local_center",
    );
    expect(screen.queryByText("暂无真实业务数据，页面入口已保留。")).not.toBeInTheDocument();
  });
});
