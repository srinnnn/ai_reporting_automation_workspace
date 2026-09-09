import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectPage } from "./ProjectPage";

const integrationProject = {
  key: "private_data_local_center",
  name: "私域数据采集中心",
  brand_key: "ANTA",
  category_key: "P1",
  status: "CONFIGURED",
  integration_key: "private-data-local-center",
  entry_path: "/integrations/private-data-local-center/#/collection/requests/new",
};

function renderProject(healthStatus: "AVAILABLE" | "UNAVAILABLE" = "AVAILABLE") {
  vi.stubGlobal("fetch", vi.fn(async (input: string | URL | Request) => {
    const path = String(input);
    const payload = path.includes("/health")
      ? {
          service: "private-data-local-center",
          status: healthStatus,
          entry_path: integrationProject.entry_path,
          message: healthStatus === "AVAILABLE" ? "采集需求服务可用" : "采集需求服务不可用",
        }
      : integrationProject;
    return { ok: true, json: async () => payload };
  }));
  const router = createMemoryRouter(
    [
      { path: "/projects/:projectKey", element: <ProjectPage /> },
      { path: "/projects", element: <div>项目管理</div> },
    ],
    { initialEntries: ["/projects/private_data_local_center"] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ProjectPage private data local center integration", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows a live entry when the collection service is available", async () => {
    renderProject("AVAILABLE");

    expect(await screen.findByRole("heading", { name: "私域数据采集中心" })).toBeInTheDocument();
    expect(await screen.findByText("AVAILABLE")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /打开采集需求页/ })).toHaveAttribute(
      "href",
      "/integrations/private-data-local-center/#/collection/requests/new",
    );
  });

  it("fails closed when the collection service is unavailable", async () => {
    renderProject("UNAVAILABLE");

    expect(await screen.findByText("UNAVAILABLE")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /打开采集需求页/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "服务不可用" })).toBeDisabled();
  });
});
