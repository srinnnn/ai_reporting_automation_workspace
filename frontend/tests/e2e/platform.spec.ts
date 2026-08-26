import { expect, test } from "@playwright/test";
// @ts-expect-error Playwright runs in Node; this project intentionally omits @types/node from app typechecking.
import { readFileSync } from "fs";

type HomepageStructureBaseline = {
  moduleOrder: string[];
  filters: string[];
  brandWorkspace: {
    selectorCount: number;
    selectedBannerCount: number;
    flatBrandCardCount: number;
    defaultBrand: string;
  };
  categoryEntries: string[];
  quickNavigation: string[];
  prohibitedPageText: string[];
  prohibitedSelectors: string[];
};

const FEEDBACK_FIXTURE = [
  { project: "P3-即时零售-安踏", mapped_project_key: "anta_retail", mapped_project_name: "安踏即时零售", brand_key: "ANTA", category_key: "P3", status: "CONNECTED", original_manual_time: "4小时", current_processing_time: "1小时", business_feedback: "ANTA真实反馈测试", iteration_need: "ANTA迭代测试", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
  { project: "P3-活动机制配置-ECCO", mapped_project_key: "ecco_activity_config", mapped_project_name: "ECCO活动配置", brand_key: "ECCO", category_key: "P3", status: "CONNECTED", original_manual_time: "3小时", current_processing_time: "1小时", business_feedback: "ECCO真实反馈测试", iteration_need: "ECCO迭代测试", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
  { project: "博西短彩信数据处理", mapped_project_key: "bosch_sms", mapped_project_name: "博西短彩信数据处理", brand_key: "BSH", category_key: "P1", status: "CONNECTED", original_manual_time: "2小时", current_processing_time: "1小时", business_feedback: "BSH真实反馈测试", iteration_need: "BSH迭代测试", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
  { project: "P1-短彩信数据处理-CK", mapped_project_key: null, mapped_project_name: null, brand_key: null, category_key: null, status: "UNMAPPED", original_manual_time: "2小时", current_processing_time: "1小时", business_feedback: "待映射真实反馈测试", iteration_need: "待映射迭代测试", updated_by: "tester", updated_at: "2026-08-26 10:00:00" },
];

const HOMEPAGE_BASELINE = JSON.parse(
  readFileSync(new URL("../../../tests/visual/baseline/homepage-structure.json", import.meta.url), "utf-8"),
) as HomepageStructureBaseline;

async function selectWorkspaceEntry(page: import("@playwright/test").Page, optionName: string) {
  await page.getByRole("combobox", { name: "选择品牌 Workspace" }).click();
  await page.getByRole("option", { name: optionName }).click();
}

async function selectGlobalFilter(page: import("@playwright/test").Page, controlName: string, optionName: string) {
  await page.getByTestId("global-filters").getByRole("combobox", { name: controlName }).click();
  await page.getByRole("option", { name: optionName }).click();
}

async function globalDashboardSnapshot(page: import("@playwright/test").Page) {
  return page.locator(
    "[data-module='global-kpi'], [data-module='global-p1-p4'], [data-module='global-projects'], [data-module='global-feedback']",
  ).allInnerTexts();
}

async function mockFeedbackApi(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/feedback*", async (route) => {
    const url = new URL(route.request().url());
    const brand = url.searchParams.get("brand");
    const records = brand ? FEEDBACK_FIXTURE.filter((record) => record.brand_key === brand) : FEEDBACK_FIXTURE;
    await route.fulfill({ contentType: "application/json", json: records, status: 200 });
  });
}

test("production runtime serves home, routes, and friendly 404", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await expect(page.getByText("品牌 Workspace 入口")).toBeVisible();

  await page.goto("/workspace/ANTA");
  await expect(page.getByRole("heading", { name: "ANTA 安踏" })).toBeVisible();

  await page.goto("/schedule");
  await expect(page).toHaveURL(/\/schedule$/);

  await page.goto("/projects");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  await page.goto("/not-a-real-route");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("homepage structural visual regression matches approved baseline contract", async ({ page }) => {
  const baseline = HOMEPAGE_BASELINE;
  await page.goto("/");

  const sidebar = page.locator(".sidebar");
  await expect(sidebar).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "项目" })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "开发排期" })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "投递资料" })).toHaveCount(0);
  await expect(sidebar.getByRole("link", { name: "最近处理记录" })).toHaveCount(0);
  await expect(page.locator(".topbar")).toBeVisible();
  await expect(page.locator(".topbar").getByRole("link", { name: "全域项目" })).toHaveAttribute("href", "/projects");
  await expect(page.locator(".topbar").getByRole("textbox", { name: "搜索暂未接入" })).toBeDisabled();
  await expect(page.locator(".topbar").getByRole("button", { name: "通知暂未接入" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "今天" })).toHaveCount(0);
  await expect(page.locator("time.date-chip")).toContainText("今天");
  await expect(page.getByRole("link", { name: /新建任务/ })).toHaveAttribute("href", "/tasks");
  await expect(page.locator(".brand-card")).toHaveCount(baseline.brandWorkspace.flatBrandCardCount);
  await expect(page.getByRole("combobox", { name: "选择品牌 Workspace" })).toHaveCount(baseline.brandWorkspace.selectorCount);
  await expect(page.getByTestId("selected-brand-banner")).toHaveCount(baseline.brandWorkspace.selectedBannerCount);
  await expect(page.getByTestId("selected-brand-banner")).toContainText(baseline.brandWorkspace.defaultBrand);
  await expect(page.getByText("待接入")).toHaveCount(0);
  await expect(page.getByTestId("global-kpi")).toHaveCount(1);

  const moduleOrder = await page.locator("[data-homepage-module='true']").evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("data-module")),
  );
  expect(moduleOrder).toEqual(baseline.moduleOrder);

  const filterLabels = await page.getByTestId("global-filters").getByRole("combobox").allInnerTexts();
  expect(filterLabels.map((label) => label.trim())).toEqual(baseline.filters);

  const categoryLabels = await page.locator(".category-card .category-badge").allInnerTexts();
  expect(categoryLabels.map((label) => label.trim())).toEqual(baseline.categoryEntries);

  const quickNavigationLabels = await page.getByTestId("quick-navigation").locator("strong").allInnerTexts();
  expect(quickNavigationLabels.map((label) => label.trim())).toEqual(baseline.quickNavigation);

  for (const text of baseline.prohibitedPageText) {
    await expect(page.locator(".page")).not.toContainText(text);
  }
  for (const selector of baseline.prohibitedSelectors) {
    await expect(page.locator(selector)).toHaveCount(0);
  }
});

test("brand selector banner enters Brand Workspace", async ({ page }) => {
  await page.goto("/");
  await selectWorkspaceEntry(page, "BSH 博西");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await page.getByRole("link", { name: /进入 Workspace/ }).click();
  await expect(page).toHaveURL(/\/workspace\/BSH$/);
  await expect(page.getByRole("heading", { name: "BSH 博西" })).toBeVisible();
});

test("Workspace Entry selector does not scope global dashboard context", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("kpi-brand-count")).toContainText("3");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("3");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("5");
  await expect(page.getByTestId("project-anta_reporting")).toBeVisible();
  await expect(page.getByTestId("project-anta_retail")).toBeVisible();
  await expect(page.getByTestId("project-bosch_sms")).toBeVisible();
  await expect(page.getByTestId("project-bosch_sms_review")).toBeVisible();
  await expect(page.getByTestId("project-ecco_activity_config")).toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("全部品牌 / 0 条");

  const globalBefore = await globalDashboardSnapshot(page);
  await selectWorkspaceEntry(page, "ECCO");

  await expect(page.getByTestId("selected-brand-banner")).toContainText("ECCO");
  await expect(page.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/ECCO");
  await expect.poll(() => globalDashboardSnapshot(page)).toEqual(globalBefore);
});

test("Global Brand Filter scopes homepage KPI, categories, projects, and feedback", async ({ page }) => {
  await page.goto("/");
  await selectWorkspaceEntry(page, "BSH 博西");

  await selectGlobalFilter(page, "品牌", "ANTA 安踏");

  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await expect(page.getByRole("link", { name: /进入 Workspace/ })).toHaveAttribute("href", "/workspace/BSH");
  await expect(page.getByTestId("kpi-brand-count")).toContainText("1");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("2");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("2");
  await expect(page.getByTestId("kpi-feedback")).toContainText("0");
  await expect(page.getByTestId("category-P1")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P2")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P3")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P4")).toContainText("暂无接入能力");
  await expect(page.getByTestId("project-anta_reporting")).toBeVisible();
  await expect(page.getByTestId("project-anta_retail")).toBeVisible();
  await expect(page.getByTestId("project-bosch_sms")).not.toBeVisible();
  await expect(page.getByTestId("project-bosch_sms_review")).not.toBeVisible();
  await expect(page.getByTestId("project-ecco_activity_config")).not.toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("ANTA 安踏 / 0 条");
  await expect(page.getByTestId("developed-feedback")).toContainText("当前暂无已接入的开发反馈数据");

  await selectGlobalFilter(page, "品牌", "BSH 博西");

  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await expect(page.getByTestId("kpi-brand-count")).toContainText("1");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("2");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("2");
  await expect(page.getByTestId("category-P1")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P2")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P3")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P4")).toContainText("1 个能力");
  await expect(page.getByTestId("project-bosch_sms")).toBeVisible();
  await expect(page.getByTestId("project-bosch_sms_review")).toBeVisible();
  await expect(page.getByTestId("project-anta_reporting")).not.toBeVisible();
  await expect(page.getByTestId("project-anta_retail")).not.toBeVisible();
  await expect(page.getByTestId("project-ecco_activity_config")).not.toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("BSH 博西 / 0 条");
  await expect(page.getByTestId("developed-feedback")).toContainText("当前暂无已接入的开发反馈数据");

  await selectGlobalFilter(page, "品牌", "ECCO");

  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await expect(page.getByTestId("kpi-brand-count")).toContainText("1");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("1");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("1");
  await expect(page.getByTestId("category-P1")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P2")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P3")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P4")).toContainText("暂无接入能力");
  await expect(page.getByTestId("project-ecco_activity_config")).toBeVisible();
  await expect(page.getByTestId("project-anta_reporting")).not.toBeVisible();
  await expect(page.getByTestId("project-anta_retail")).not.toBeVisible();
  await expect(page.getByTestId("project-bosch_sms")).not.toBeVisible();
  await expect(page.getByTestId("project-bosch_sms_review")).not.toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("ECCO / 0 条");
  await expect(page.getByTestId("developed-feedback")).toContainText("当前暂无已接入的开发反馈数据");
});

test("Brand Workspace pages only render current-brand projects and feedback context", async ({ page }) => {
  await page.goto("/workspace/ANTA");
  await expect(page.getByTestId("brand-kpi")).toContainText("2");
  await expect(page.getByTestId("brand-projects")).toContainText("安踏周报/月报");
  await expect(page.getByTestId("brand-projects")).toContainText("安踏即时零售");
  await expect(page.getByTestId("brand-projects")).not.toContainText("博西短彩信数据处理");
  await expect(page.getByTestId("brand-projects")).not.toContainText("ECCO活动配置");
  await expect(page.getByTestId("brand-feedback")).toContainText("ANTA 安踏 / 0 条");

  await page.goto("/workspace/BSH");
  await expect(page.getByTestId("brand-kpi")).toContainText("2");
  await expect(page.getByTestId("brand-projects")).toContainText("博西短彩信数据处理");
  await expect(page.getByTestId("brand-projects")).toContainText("博世/西门子短彩信规划复核");
  await expect(page.getByTestId("brand-projects")).not.toContainText("安踏周报/月报");
  await expect(page.getByTestId("brand-projects")).not.toContainText("ECCO活动配置");
  await expect(page.getByTestId("brand-feedback")).toContainText("BSH 博西 / 0 条");

  await page.goto("/workspace/ECCO");
  await expect(page.getByTestId("brand-kpi")).toContainText("1");
  await expect(page.getByTestId("brand-projects")).toContainText("ECCO活动配置");
  await expect(page.getByTestId("brand-projects")).not.toContainText("安踏周报/月报");
  await expect(page.getByTestId("brand-projects")).not.toContainText("博西短彩信数据处理");
  await expect(page.getByTestId("brand-feedback")).toContainText("ECCO / 0 条");
});

test("real feedback state follows Global Filters while Workspace Entry remains independent", async ({ page }) => {
  await mockFeedbackApi(page);
  await page.goto("/");

  await expect(page.getByTestId("kpi-feedback")).toContainText("4");
  await expect(page.getByTestId("developed-feedback")).toContainText("ANTA真实反馈测试");
  await expect(page.getByTestId("developed-feedback")).toContainText("ECCO真实反馈测试");
  await expect(page.getByTestId("developed-feedback")).toContainText("BSH真实反馈测试");
  await expect(page.getByTestId("developed-feedback")).toContainText("待映射真实反馈测试");

  await selectWorkspaceEntry(page, "ECCO");
  await expect(page.getByTestId("kpi-feedback")).toContainText("4");
  await expect(page.getByTestId("developed-feedback")).toContainText("待映射真实反馈测试");

  await selectGlobalFilter(page, "品牌", "ANTA 安踏");
  await expect(page.getByTestId("kpi-feedback")).toContainText("1");
  await expect(page.getByTestId("developed-feedback")).toContainText("ANTA真实反馈测试");
  await expect(page.getByTestId("developed-feedback")).not.toContainText("ECCO真实反馈测试");
  await expect(page.getByTestId("developed-feedback")).not.toContainText("BSH真实反馈测试");
  await expect(page.getByTestId("developed-feedback")).not.toContainText("待映射真实反馈测试");

  await page.goto("/workspace/ANTA");
  await expect(page.getByTestId("brand-feedback")).toContainText("ANTA真实反馈测试");
  await expect(page.getByTestId("brand-feedback")).not.toContainText("ECCO真实反馈测试");
  await expect(page.getByTestId("brand-feedback")).not.toContainText("BSH真实反馈测试");
  await expect(page.getByTestId("brand-feedback")).not.toContainText("待映射真实反馈测试");
});

test("P1-P4 category navigation keeps selected brand and prevents cross-category leakage", async ({ page }) => {
  await page.goto("/workspace/ANTA");

  await page.getByTestId("category-P1").click();
  await expect(page).toHaveURL(/\/workspace\/ANTA\/P1$/);
  await expect(page.locator(".project-row")).toHaveCount(1);

  await page.goto("/workspace/ANTA/P2");
  await expect(page.locator(".project-row")).toHaveCount(0);
  await expect(page.getByText(/暂无/)).toBeVisible();

  await page.goto("/workspace/ANTA/P3");
  await expect(page.locator(".project-row")).toHaveCount(1);

  await page.goto("/workspace/ANTA/P4");
  await expect(page.locator(".project-row")).toHaveCount(0);
});

test("captures runtime visual evidence at approved desktop viewport", async ({ page }) => {
  expect(page.viewportSize()).toEqual({ width: 1440, height: 1000 });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/homepage-global.png", fullPage: true });
  await page.screenshot({ path: "../tests/visual/runtime/homepage-workspace-entry-anta.png", fullPage: true });

  const globalBefore = await globalDashboardSnapshot(page);
  await selectWorkspaceEntry(page, "ECCO");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("ECCO");
  await expect.poll(() => globalDashboardSnapshot(page)).toEqual(globalBefore);
  await page.screenshot({ path: "../tests/visual/runtime/homepage-workspace-entry-ecco.png", fullPage: true });

  await selectGlobalFilter(page, "品牌", "ANTA 安踏");
  await expect(page.getByTestId("kpi-brand-count")).toContainText("1");
  await page.screenshot({ path: "../tests/visual/runtime/homepage-global-filter-anta.png", fullPage: true });

  await page.goto("/workspace/ANTA");
  await expect(page.getByRole("heading", { name: "ANTA 安踏" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/workspace-anta.png", fullPage: true });

  await page.goto("/workspace/ECCO");
  await expect(page.getByRole("heading", { name: "ECCO" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/workspace-ecco.png", fullPage: true });

  await page.goto("/workspace/BSH");
  await expect(page.getByRole("heading", { name: "BSH 博西" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/workspace-bsh.png", fullPage: true });
});
