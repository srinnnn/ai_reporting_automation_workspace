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

const HOMEPAGE_BASELINE = JSON.parse(
  readFileSync(new URL("../../../tests/visual/baseline/homepage-structure.json", import.meta.url), "utf-8"),
) as HomepageStructureBaseline;

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

  await expect(page.locator(".sidebar")).toBeVisible();
  await expect(page.locator(".topbar")).toBeVisible();
  await expect(page.locator(".brand-card")).toHaveCount(baseline.brandWorkspace.flatBrandCardCount);
  await expect(page.getByRole("combobox", { name: "品牌" })).toHaveCount(baseline.brandWorkspace.selectorCount);
  await expect(page.getByTestId("selected-brand-banner")).toHaveCount(baseline.brandWorkspace.selectedBannerCount);
  await expect(page.getByTestId("selected-brand-banner")).toContainText(baseline.brandWorkspace.defaultBrand);
  await expect(page.getByText("待接入")).toHaveCount(0);
  await expect(page.getByTestId("selected-brand-kpi")).toHaveCount(1);

  const moduleOrder = await page.locator("[data-homepage-module='true']").evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("data-module")),
  );
  expect(moduleOrder).toEqual(baseline.moduleOrder);

  const filterLabels = await page.getByTestId("global-filters").locator("button").allInnerTexts();
  expect(filterLabels.map((label) => label.trim())).toEqual(baseline.filters);

  const categoryLabels = await page.locator(".category-card strong").allInnerTexts();
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
  await page.getByRole("combobox", { name: "品牌" }).selectOption("BSH");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await page.getByRole("link", { name: /进入 Workspace/ }).click();
  await expect(page).toHaveURL(/\/workspace\/BSH$/);
  await expect(page.getByRole("heading", { name: "BSH 博西" })).toBeVisible();
});

test("brand selection scopes ANTA, BSH, and ECCO homepage context", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("combobox", { name: "品牌" }).selectOption("ANTA");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("ANTA 安踏");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("2");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("2");
  await expect(page.getByTestId("kpi-feedback")).toContainText("未接入");
  await expect(page.getByTestId("kpi-feedback")).not.toContainText("0");
  await expect(page.getByTestId("category-P1")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P2")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P3")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P4")).toContainText("暂无接入能力");
  await expect(page.getByTestId("project-anta_reporting")).toBeVisible();
  await expect(page.getByTestId("project-anta_retail")).toBeVisible();
  await expect(page.getByTestId("project-bosch_sms")).not.toBeVisible();
  await expect(page.getByTestId("project-ecco_activity_config")).not.toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("ANTA 安踏 / 未接入");
  await expect(page.getByTestId("developed-feedback")).toContainText("当前品牌暂无反馈记录");

  await page.getByRole("combobox", { name: "品牌" }).selectOption("BSH");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("2");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("2");
  await expect(page.getByTestId("category-P1")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P2")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P3")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P4")).toContainText("1 个能力");
  await expect(page.getByTestId("project-bosch_sms")).toBeVisible();
  await expect(page.getByTestId("project-bosch_sms_review")).toBeVisible();
  await expect(page.getByTestId("project-anta_reporting")).not.toBeVisible();
  await expect(page.getByTestId("project-ecco_activity_config")).not.toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("BSH 博西 / 未接入");
  await expect(page.getByTestId("developed-feedback")).toContainText("当前品牌暂无反馈记录");

  await page.getByRole("combobox", { name: "品牌" }).selectOption("ECCO");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("ECCO");
  await expect(page.getByTestId("kpi-active-categories")).toContainText("1");
  await expect(page.getByTestId("kpi-connected-projects")).toContainText("1");
  await expect(page.getByTestId("category-P1")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P2")).toContainText("暂无接入能力");
  await expect(page.getByTestId("category-P3")).toContainText("1 个能力");
  await expect(page.getByTestId("category-P4")).toContainText("暂无接入能力");
  await expect(page.getByTestId("project-ecco_activity_config")).toBeVisible();
  await expect(page.getByTestId("project-anta_reporting")).not.toBeVisible();
  await expect(page.getByTestId("project-bosch_sms")).not.toBeVisible();
  await expect(page.getByTestId("developed-feedback")).toContainText("ECCO / 未接入");
  await expect(page.getByTestId("developed-feedback")).toContainText("当前品牌暂无反馈记录");
});

test("P1-P4 category navigation keeps selected brand and prevents cross-category leakage", async ({ page }) => {
  await page.goto("/workspace/ANTA");

  await page.getByRole("link", { name: /P1/ }).click();
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
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/homepage.png", fullPage: true });
  await page.screenshot({ path: "../tests/visual/runtime/homepage-anta.png", fullPage: true });

  await page.getByRole("combobox", { name: "品牌" }).selectOption("BSH");
  await page.screenshot({ path: "../tests/visual/runtime/homepage-bsh.png", fullPage: true });

  await page.getByRole("combobox", { name: "品牌" }).selectOption("ECCO");
  await page.screenshot({ path: "../tests/visual/runtime/homepage-ecco.png", fullPage: true });

  await page.goto("/workspace/ANTA");
  await page.screenshot({ path: "../tests/visual/runtime/workspace-anta.png", fullPage: true });
});
