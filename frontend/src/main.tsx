import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppLayout } from "./app/AppLayout";
import { CategoryPage } from "./pages/CategoryPage";
import { HomePage } from "./pages/HomePage";
import { ModulePage } from "./pages/ModulePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProjectPage } from "./pages/ProjectPage";
import { SchedulePage } from "./pages/SchedulePage";
import { WorkspacePage } from "./pages/WorkspacePage";
import "./styles.css";

const queryClient = new QueryClient();

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "workspace/:brandKey", element: <WorkspacePage /> },
      { path: "workspace/:brandKey/:categoryKey", element: <CategoryPage /> },
      { path: "projects", element: <ModulePage title="项目管理" moduleKey="projects" /> },
      { path: "projects/:projectKey", element: <ProjectPage /> },
      { path: "schedule", element: <SchedulePage /> },
      { path: "data-foundation", element: <ModulePage title="数据入库中心" moduleKey="data-foundation" /> },
      { path: "tasks", element: <ModulePage title="自动化执行" moduleKey="tasks" /> },
      { path: "reports", element: <ModulePage title="报表中心" moduleKey="reports" /> },
      { path: "resources", element: <ModulePage title="资源管理" /> },
      { path: "data", element: <ModulePage title="数据中心" /> },
      { path: "system", element: <ModulePage title="系统管理" /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
