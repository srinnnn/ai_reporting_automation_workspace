import { expect, test } from "@playwright/test";

test("production runtime serves home, routes, and friendly 404", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await expect(page.getByText("品牌 Workspace 入口")).toBeVisible();

  await page.goto("/workspace/ANTA");
  await expect(page.getByText("未知品牌")).toBeVisible();

  await page.goto("/schedule");
  await expect(page.getByRole("heading", { name: "开发排期" })).toBeVisible();

  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "项目管理", level: 1 })).toBeVisible();

  await page.goto("/not-a-real-route");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("captures runtime homepage visual evidence", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "中台全局首页" })).toBeVisible();
  await page.screenshot({ path: "../tests/visual/runtime/homepage.png", fullPage: true });
});
