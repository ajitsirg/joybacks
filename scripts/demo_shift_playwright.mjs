/**
 * Playwright demo: Shift Associate on joyclubs.in
 * Screenshots each step. Shifts a leaf, then restores original sponsor.
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = "https://joyclubs.in";
const OUT = path.resolve("scripts/demo-shift-screens");
const EMAIL = "ajit@accounts.dovix.ai";
const PASSWORD = "ajit@123";

const MOVE_ID = "JOY9351777378";
const NEW_SPONSOR = "JOY7014458417";
const ORIGINAL_SPONSOR = "JOY7891695113";

fs.mkdirSync(OUT, { recursive: true });

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log("screenshot", file);
}

async function openShiftPage(page) {
  // Prefer sidebar click (SPA) — full reload can race auth and bounce to tree
  const link = page.getByRole("link", { name: /Shift Associate/i });
  if (await link.count()) {
    await link.first().click();
  } else {
    await page.goto(`${BASE}/genealogy/shift`, { waitUntil: "domcontentloaded" });
  }
  await page.getByRole("button", { name: /Shift now/i }).waitFor({ timeout: 20000 });
  await page.waitForTimeout(500);
}

async function doShift(page, from, under, tag) {
  const fromBox = page.locator("#from-id");
  const underBox = page.locator("#under-id");
  await fromBox.fill("");
  await fromBox.fill(from);
  await page.waitForTimeout(1000);
  await underBox.fill("");
  await underBox.fill(under);
  await page.waitForTimeout(1000);
  await shot(page, `${tag}-filled`);

  page.once("dialog", async (dialog) => {
    console.log("confirm:", dialog.message().replace(/\n/g, " | ").slice(0, 160));
    await dialog.accept();
  });
  await page.getByRole("button", { name: /Shift now/i }).click();
  await page.getByText(/Shift complete|People moved|Shifted/i).first().waitFor({ timeout: 45000 });
  await page.waitForTimeout(600);
  await shot(page, `${tag}-done`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true,
  });

  console.log("1) Login (Staff)");
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await shot(page, "01-login");
  await page.getByRole("button", { name: /^Staff$/i }).click();
  await page.locator('input[type="email"], input[name="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASSWORD);
  await shot(page, "02-login-filled");
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(/dashboard/, { timeout: 30000 });
  await page.waitForTimeout(1200);
  await shot(page, "03-dashboard");

  console.log("2) Open Shift Associate");
  await openShiftPage(page);
  await shot(page, "04-shift-page");

  console.log(`3) Shift ${MOVE_ID} under ${NEW_SPONSOR}`);
  await doShift(page, MOVE_ID, NEW_SPONSOR, "05-shift");

  console.log("4) Tree focused on new sponsor");
  await page.goto(`${BASE}/genealogy?focus=${NEW_SPONSOR}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);
  await shot(page, "06-tree-after-shift");

  console.log(`5) Restore ${MOVE_ID} under ${ORIGINAL_SPONSOR}`);
  await openShiftPage(page);
  await doShift(page, MOVE_ID, ORIGINAL_SPONSOR, "07-restore");

  console.log("6) Tree restored");
  await page.goto(`${BASE}/genealogy?focus=${ORIGINAL_SPONSOR}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);
  await shot(page, "08-tree-restored");

  await browser.close();
  console.log("\nDemo complete →", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
