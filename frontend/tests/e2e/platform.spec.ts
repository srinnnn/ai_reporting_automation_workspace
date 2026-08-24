import { expect, test } from "@playwright/test";

type HomepageStructureBaseline = {
  filters: string[];
  brandWorkspace: {
    selectorCount: number;
    selectedBannerCount: number;
    flatBrandCardCount: number;
    defaultBrand: string;
  };
  categoryEntries: string[];
};

const HOMEPAGE_BASELINE: HomepageStructureBaseline = {
  filters: ["项目", "品牌", "优先级", "状态"],
  brandWorkspace: {
    selectorCount: 1,
    selectedBannerCount: 1,
    flatBrandCardCount: 0,
    defaultBrand: "ANTA 安踏",
  },
  categoryEntries: ["P1", "P2", "P3", "P4"],
};

test("production runtime serves home, routes, and friendly 404", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await expect(page.getByText("品牌 Workspace 入口")).toBeVisible();

  await page.goto("/workspace/ANTA");
  await expect(page.getByRole("heading", { name: "ANTA 安踏" })).toBeVisible();

  await page.goto("/schedule");
  await expect(page.getByRole("heading", { name: "开发排期" })).toBeVisible();

  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "项目管理", level: 1 })).toBeVisible();

  await page.goto("/not-a-real-route");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("homepage structural visual regression matches approved baseline contract", async ({ page }) => {
  const baseline = HOMEPAGE_BASELINE;
  await page.goto("/");

  await expect(page.locator(".brand-card")).toHaveCount(baseline.brandWorkspace.flatBrandCardCount);
  await expect(page.getByRole("combobox", { name: "品牌" })).toHaveCount(baseline.brandWorkspace.selectorCount);
  await expect(page.getByTestId("selected-brand-banner")).toHaveCount(baseline.brandWorkspace.selectedBannerCount);
  await expect(page.getByTestId("selected-brand-banner")).toContainText(baseline.brandWorkspace.defaultBrand);

  const filterLabels = await page.getByTestId("global-filters").locator("button").allInnerTexts();
  expect(filterLabels.map((label) => label.trim())).toEqual(baseline.filters);

  const categoryLabels = await page.locator(".category-card strong").allInnerTexts();
  expect(categoryLabels.map((label) => label.trim())).toEqual(baseline.categoryEntries);
});

test("brand selector banner enters Brand Workspace", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("combobox", { name: "品牌" }).selectOption("BSH");
  await expect(page.getByTestId("selected-brand-banner")).toContainText("BSH 博西");
  await page.getByRole("link", { name: /进入 Brand Workspace/ }).click();
  await expect(page).toHaveURL(/\/workspace\/BSH$/);
  await expect(page.getByRole("heading", { name: "BSH 博西" })).toBeVisible();
});

test("P1-P4 category navigation keeps selected brand and prevents cross-category leakage", async ({ page }) => {
  await page.goto("/workspace/ANTA");

  await page.getByRole("link", { name: /P1/ }).click();
  await expect(page).toHaveURL(/\/workspace\/ANTA\/P1$/);
  await expect(page.getByText("安踏周报/月报")).toBeVisible();
  await expect(page.getByText("安踏即时零售")).not.toBeVisible();
  await expect(page.getByText("ECCO活动配置")).not.toBeVisible();

  await page.goto("/workspace/ANTA/P2");
  await expect(page.getByText("当前品牌暂无接入能力")).toBeVisible();
  await expect(page.getByText("AI选品辅助")).not.toBeVisible();
  await expect(page.getByText("文案内容辅助")).not.toBeVisible();

  await page.goto("/workspace/ANTA/P3");
  await expect(page.getByText("安踏即时零售")).toBeVisible();
  await expect(page.getByText("安踏周报/月报")).not.toBeVisible();
  await expect(page.getByText("ECCO活动配置")).not.toBeVisible();

  await page.goto("/workspace/ANTA/P4");
  await expect(page.getByText("当前品牌暂无接入能力")).toBeVisible();
  await expect(page.getByText("博世/西门子短彩信规划复核")).not.toBeVisible();
});

test("captures runtime homepage visual evidence", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/homepage.png", fullPage: true });
});
