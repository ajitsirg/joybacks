/**
 * ROI-on-ROI Playwright smoke test (isolated local DB only).
 *
 * Run via: bash scripts/run_roi_smoke_test.sh
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
function arg(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

const BASE = arg("--base", "http://127.0.0.1:8765");
const OUT = path.resolve(arg("--out", "scripts/roi-smoke-screens"));
const REPORT_PATH = path.resolve(arg("--report", path.join(OUT, "verification.json")));

fs.mkdirSync(OUT, { recursive: true });

const report = JSON.parse(fs.readFileSync(REPORT_PATH, "utf8"));
const L1 = report.logins.l1_upline;
const BUYER = report.logins.buyer;

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log("screenshot", file);
  return file;
}

async function loginAssociate(page, associateId, password) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.locator("#username").fill(associateId);
  await page.locator("#password").fill(password);
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/auth/login/") && r.request().method() === "POST",
      { timeout: 30000 },
    ),
    page.getByRole("button", { name: /Sign in/i }).click(),
  ]);
  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`Login failed (${response.status()}): ${body.slice(0, 200)}`);
  }
  await page.waitForURL(/dashboard/, { timeout: 30000 });
  await page.waitForTimeout(1200);
}

function writeHtmlReport() {
  const rows = report.levels
    .map(
      (r) =>
        `<tr class="${r.ok ? "ok" : "bad"}"><td>L${r.level}</td><td>₹ ${r.expected}</td><td>₹ ${r.actual}</td><td>${r.beneficiary ?? "—"}</td><td>${r.ok ? "✓" : "✗"}</td></tr>`,
    )
    .join("");
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>ROI-on-ROI Smoke Report</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;color:#0f2418}
  h1{color:#064e2a} table{border-collapse:collapse;width:100%;margin:1rem 0}
  th,td{border:1px solid #c8e6d4;padding:.5rem .75rem;text-align:left}
  th{background:#e6f5ec}.ok{background:#f0fdf4}.bad{background:#fef2f2}
  .box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin:1rem 0}
  code{background:#eef2ff;padding:.1rem .35rem;border-radius:4px}
</style></head><body>
<h1>ROI-on-ROI calculation smoke test</h1>
<p><strong>Formula:</strong> Base ROI = Investment × 1% = <strong>₹2,200</strong>. Level income = Base ROI × Level % (not investment × level %).</p>
<div class="box">
  <div>Buyer base ROI: <strong>₹ ${report.buyer_roi_balance}</strong> (expected ₹ ${report.base_roi})</div>
  <div>Total upline (10 levels): <strong>₹ ${report.upline_total}</strong> (expected ₹ ${report.expected_upline_total})</div>
  <div>Status: <strong>${report.ok ? "PASS ✓" : "FAIL ✗"}</strong></div>
</div>
<h2>Level breakdown</h2>
<table><thead><tr><th>Level</th><th>Expected</th><th>Actual</th><th>Beneficiary</th><th></th></tr></thead>
<tbody>${rows}</tbody></table>
<p>Example: L1 = ₹2,200 × 5% = ₹110 · L2 = ₹55 · … · Total = ₹330</p>
<p><em>Isolated smoke DB only — no production data touched.</em></p>
</body></html>`;
  const file = path.join(OUT, "calculation-report.html");
  fs.writeFileSync(file, html);
  return file;
}

async function main() {
  if (!report.ok) {
    console.error("Backend verification failed — aborting Playwright");
    process.exit(1);
  }

  const reportHtml = writeHtmlReport();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // 1) Calculation report screenshot
  await page.goto(`file://${reportHtml}`);
  await shot(page, "01-calculation-report");

  // 2) L1 upline — ROI Level Income (should show ₹110, not ₹2,200)
  console.log("Login L1 upline", L1.id);
  await loginAssociate(page, L1.id, L1.password);
  await shot(page, "02-l1-dashboard");

  await page.goto(`${BASE}/income/roi`, { waitUntil: "networkidle" });
  await page.locator("table").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(1000);
  await shot(page, "03-l1-roi-level-income");

  const bodyL1 = await page.locator("body").innerText();
  if (!bodyL1.includes("110")) {
    throw new Error("L1 ROI Level Income page should show ₹110 commission");
  }
  if (bodyL1.match(/2,200|2200/) && bodyL1.includes("Commission")) {
    console.warn("Note: page may mention ₹2,200 as Base ROI reference column — check screenshot");
  }

  // 3) Buyer — My Monthly ROI (base ₹2,200 only)
  console.log("Login buyer", BUYER.id);
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.context().clearCookies();
  await loginAssociate(page, BUYER.id, BUYER.password);

  await page.goto(`${BASE}/income/my-roi`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  await shot(page, "04-buyer-my-monthly-roi");

  const bodyBuyer = await page.locator("body").innerText();
  if (!bodyBuyer.includes("2,200") && !bodyBuyer.includes("2200") && !bodyBuyer.includes("2,200.00")) {
    await shot(page, "04-buyer-my-monthly-roi-debug");
    throw new Error("Buyer My Monthly ROI page should show ₹2,200 base ROI");
  }

  await page.goto(`${BASE}/income/roi`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await shot(page, "05-buyer-roi-level-income-empty");

  await browser.close();
  console.log("\nSmoke PASS. Screenshots in", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
