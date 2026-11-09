import { mkdirSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const root = "../docs/web-review";

async function shoot(page: Page, dir: string, name: string, width: number, height: number) {
  mkdirSync(`${root}/${dir}`, { recursive: true });
  await page.setViewportSize({ width, height });
  await page.evaluate("document.fonts.ready");
  await page.screenshot({ path: `${root}/${dir}/${name}-${width}x${height}.png` });
}

function watch(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    if (text.includes("Failed to load resource") || text.includes("ERR_CONNECTION") || text.includes("favicon")) return;
    errors.push(text);
  });
  return errors;
}

test("launcher, demo shell, and member surfaces", async ({ page }) => {
  const errors = watch(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "One approved answer, in the place each person already works." })).toBeVisible();
  await shoot(page, "m2", "launcher", 1440, 900);
  await shoot(page, "m2", "launcher", 1280, 800);

  await page.goto("/demo?step=0");
  await expect(page.getByRole("heading", { name: "Today: one disclaimer, three wordings" })).toBeVisible();
  await shoot(page, "m2", "demo-step-0", 1440, 900);
  await shoot(page, "m2", "demo-step-0", 1280, 800);

  await page.goto("/explore/pharmacy");
  await expect(page.getByRole("heading", { name: "Suggested for this call" })).toBeVisible();
  await shoot(page, "m4", "pharmacy-desktop", 1440, 900);
  await shoot(page, "m4", "pharmacy-desktop", 1280, 800);

  await page.goto("/explore/insurance");
  await expect(page.getByRole("heading", { name: "Suggested for this call" })).toBeVisible();
  await shoot(page, "m4", "insurance-desktop", 1440, 900);
  await shoot(page, "m4", "insurance-desktop", 1280, 800);

  await page.goto("/explore/member?view=website");
  await expect(page.getByRole("heading", { name: "Estimate a drug price" })).toBeVisible();
  await shoot(page, "m3", "member-website", 1440, 900);
  await shoot(page, "m3", "member-website", 1280, 800);
  await page.screenshot({ path: `${root}/m3/member-website-full.png`, fullPage: true });

  await page.getByRole("button", { name: "Ask Harbor" }).first().click();
  await expect(page.getByRole("region", { name: "Ask Harbor" })).toBeVisible();
  await page.waitForTimeout(300);
  await shoot(page, "m3", "member-chat", 1440, 900);
  await shoot(page, "m3", "member-chat", 1280, 800);

  await page.goto("/explore/member?view=app");
  await expect(page.getByRole("banner", { name: "Harbor Health app" })).toBeVisible();
  await shoot(page, "m3", "member-app", 1440, 900);
  await shoot(page, "m3", "member-app", 1280, 800);

  await page.goto("/explore/member?view=phone");
  await expect(page.getByRole("heading", { name: "Harbor Health automated line" })).toBeVisible();
  await shoot(page, "m3", "member-phone", 1440, 900);
  await shoot(page, "m3", "member-phone", 1280, 800);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/explore/member?view=app");
  await expect(page.getByRole("navigation", { name: "App" })).toBeVisible();
  await page.evaluate("document.fonts.ready");
  await page.screenshot({ path: `${root}/m3/member-app-390x844.png` });

  await page.goto("/explore/member?view=website&chat=open");
  await expect(page.getByRole("dialog", { name: "Ask Harbor" })).toBeVisible();
  await page.waitForTimeout(300);
  await page.evaluate("document.fonts.ready");
  await page.screenshot({ path: `${root}/m3/member-website-390x844.png` });

  expect(errors, errors.join("\n")).toEqual([]);
});
