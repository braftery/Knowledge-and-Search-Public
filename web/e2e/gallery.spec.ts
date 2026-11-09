import { test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const frames: Array<{ id: string; height: number }> = [
  { id: "cover", height: 400 },
  { id: "button", height: 400 },
  { id: "status-badge", height: 400 },
  { id: "tabs", height: 400 },
  { id: "field", height: 400 },
  { id: "toast", height: 400 },
  { id: "verbatim", height: 400 },
  { id: "citation", height: 400 },
  { id: "diff", height: 400 },
  { id: "answer-card", height: 400 },
  { id: "empty", height: 432 },
  { id: "skeleton", height: 400 },
  { id: "table", height: 400 },
  { id: "metric", height: 400 },
  { id: "ranked", height: 400 },
  { id: "presenter", height: 400 },
  { id: "launcher", height: 400 },
  { id: "chat", height: 740 },
];

test("gallery frames and pages", async ({ page }) => {
  const root = "../docs/web-review/m1";
  await mkdir(root, { recursive: true });

  for (const frame of frames) {
    await page.setViewportSize({ width: 960, height: frame.height });
    await page.goto(`/gallery/${frame.id}`);
    await page.locator(`#${frame.id}`).screenshot({ path: `${root}/${frame.id}.png` });
  }

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery");
  await page.screenshot({ path: `${root}/gallery-1440x900.png`, fullPage: true });

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/gallery");
  await page.screenshot({ path: `${root}/gallery-1280x800.png`, fullPage: true });
});
