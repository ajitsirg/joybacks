/**
 * Ajit + 25 dummy smoke — Playwright screenshots (isolated local DB only).
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
const OUT = path.resolve(arg("--out", "scripts/ajit25-smoke-screens"));
const REPORT_PATH = path.resolve(arg("--report", path.join(OUT, "verification.json")));

fs.mkdirSync(OUT, { recursive: true });
const report = JSON.parse(fs.readFileSync(REPORT_PATH, "utf8"));
const shots = [];

function bodyHasAmount(body, raw) {
  const compact = String(body).replace(/[₹,\s]/g, "");
  const variants = [
    String(raw),
    String(raw).replace(/\.00$/, ""),
    Number(raw).toLocaleString("en-IN"),
    Number(raw).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  ];
  return variants.some((v) => body.includes(v) || compact.includes(String(v).replace(/[₹,\s]/g, "")));
}

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log("screenshot", file);
  shots.push({ name, file, pass: true });
  return file;
}

async function assertVisible(page, name, needles) {
  const body = await page.locator("body").innerText();
  const missing = [];
  for (const raw of needles) {
    if (!bodyHasAmount(body, raw) && !body.includes(String(raw))) missing.push(String(raw));
  }
  if (missing.length) {
    const row = shots.find((s) => s.name === name) || { name, pass: false };
    row.pass = false;
    row.missing = missing;
    if (!shots.includes(row) && !shots.find((s) => s.name === name)) shots.push(row);
    const existing = shots.find((s) => s.name === name);
    if (existing) {
      existing.pass = false;
      existing.missing = missing;
    }
    throw new Error(`${name}: missing visible ${missing.join(", ")}`);
  }
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
  await page.waitForResponse(
    (r) => r.url().includes("/dashboard/admin") && r.ok(),
    { timeout: 30000 },
  ).catch(() => {});
  await page.waitForTimeout(2000);
}

async function logout(page) {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.context().clearCookies();
}

function parseInr(raw) {
  const n = Number(String(raw ?? "").replace(/[₹,\s]/g, ""));
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : NaN;
}

async function assertLevel1Table(page, name) {
  const table = page.locator("table").filter({ has: page.locator("th", { hasText: "Earned" }) }).first();
  const row = table.locator("tr").filter({ hasText: "Level 1" }).first();
  await row.waitFor({ timeout: 20000 });
  const cells = (await row.locator("td").allInnerTexts()).map((t) => t.trim());
  if (cells.length < 4) {
    throw new Error(`${name}: Level 1 row incomplete (${cells.join(" | ")})`);
  }
  const pct = Number(String(cells[1]).replace(/%/g, "").trim());
  const base = parseInr(cells[2]);
  const earned = parseInr(cells[3]);
  const expected = Math.round(((base * pct) / 100) * 100) / 100;
  if (!Number.isFinite(pct) || !Number.isFinite(base) || !Number.isFinite(earned)) {
    throw new Error(`${name}: could not parse L1 cells ${cells.join(" | ")}`);
  }
  if (Math.abs(expected - earned) > 0.02) {
    throw new Error(`${name}: L1 earned ₹${earned} != ${pct}% of ₹${base} (₹${expected})`);
  }
  const existing = shots.find((s) => s.name === name);
  if (existing) existing.l1 = { pct, base, earned, expected };
}

async function assertNavHasReward(page, expected) {
  const nav = await page.locator("nav").first().innerText();
  const has = /Reward Income/i.test(nav);
  if (has !== expected) {
    throw new Error(
      expected
        ? "Associate sidebar missing Reward Income"
        : "Super admin sidebar still shows Reward Income",
    );
  }
}

function writeHtmlReport() {
  const saleRows = (report.sale?.levels ?? [])
    .map(
      (r) =>
        `<tr class="${r.ok ? "ok" : "bad"}"><td>L${r.level}</td><td>${r.percent}%</td><td>${r.sale_count}</td><td>₹ ${r.per_sale}</td><td>₹ ${r.expected}</td><td>₹ ${r.actual}</td><td>${r.ok ? "✓" : "✗"}</td></tr>`,
    )
    .join("");
  const roiRows = (report.roi?.levels ?? [])
    .map(
      (r) =>
        `<tr class="${r.ok ? "ok" : "bad"}"><td>L${r.level}</td><td>₹ ${r.expected}</td><td>₹ ${r.actual}</td><td>${r.beneficiary ?? "—"}</td><td>${r.ok ? "✓" : "✗"}</td></tr>`,
    )
    .join("");
  const rewardRows = (report.reward?.milestones ?? [])
    .map(
      (m) =>
        `<tr><td>M${m.sno}</td><td>${m.status}</td><td>₹ ${m.reward}</td><td>₹ ${m.total}</td><td>₹ ${m.leg1} / ${m.leg2} / ${m.leg3}</td><td>remain ${m.remaining_total ?? ""} / ${m.remaining_leg1 ?? ""} / ${m.remaining_leg2 ?? ""} / ${m.remaining_leg3 ?? ""}</td></tr>`,
    )
    .join("");
  const shotRows = (report.screenshots ?? [])
    .map(
      (s) =>
        `<tr class="${s.pass ? "ok" : "bad"}"><td>${s.name}</td><td>${s.pass ? "PASS" : "FAIL"}</td><td>${(s.missing || []).join(", ") || "—"}</td></tr>`,
    )
    .join("");
  const benRows = (report.sale?.by_beneficiary ?? [])
    .map((b) => {
      const lv = (b.levels ?? [])
        .map((l) => `L${l.level}×${l.count}=₹${l.actual}`)
        .join("; ");
      return `<tr class="${b.ok ? "ok" : "bad"}"><td>${b.id}</td><td>₹ ${b.total}</td><td>${lv}</td></tr>`;
    })
    .join("");
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Ajit 25-ID Smoke Report</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#0f2418}
  h1,h2{color:#064e2a} table{border-collapse:collapse;width:100%;margin:1rem 0}
  th,td{border:1px solid #c8e6d4;padding:.45rem .7rem;text-align:left;font-size:14px}
  th{background:#e6f5ec}.ok{background:#f0fdf4}.bad{background:#fef2f2}
  .box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin:1rem 0}
</style></head><body>
<h1>Ajit + 25 dummy smoke test</h1>
<p>Isolated local DB only. Dummy prefix <code>JOYSMK25*</code>. Not production.</p>
<div class="box">
  <div>Overall: <strong>${report.ok ? "PASS ✓" : "FAIL ✗"}</strong></div>
  <div>Head: ${report.head.id} (${report.head.name})</div>
  <div>Downline 25: ${report.counts.downline_25} · ROI extras: ${report.counts.roi_extras}</div>
  <div>Sale unlock: ${report.head.unlocked_sale_levels} · ROI unlock: ${report.head.unlocked_roi_levels}</div>
  <div>Ajit wallets — Income ₹${report.head.income_wallet} · ROI ₹${report.head.roi_wallet} · Reward ₹${report.head.reward_wallet}</div>
  <div>Tiles — Referral ₹${report.tiles?.referral_income} · Level ₹${report.tiles?.level_income} · ROI ₹${report.tiles?.roi_income} · Reward ₹${report.tiles?.reward_income}</div>
</div>
<h2>Sale commission (principal × %)</h2>
<p>${report.sale.formula}. Ajit total actual ₹${report.sale.total_actual}</p>
<table><thead><tr><th>Level</th><th>%</th><th>Sales</th><th>Per sale</th><th>Expected</th><th>Actual</th><th></th></tr></thead>
<tbody>${saleRows}</tbody></table>
<h2>Sale by beneficiary</h2>
<table><thead><tr><th>ID</th><th>Total</th><th>Levels</th></tr></thead>
<tbody>${benRows}</tbody></table>
<h2>ROI-on-ROI from ${report.roi.deepest_buyer}</h2>
<p>${report.roi.formula}. Buyer ROI wallet ₹${report.roi.buyer_roi_balance} (must be 0). Upline ₹${report.roi.upline_total} expected ₹330.</p>
<table><thead><tr><th>Level</th><th>Expected</th><th>Actual</th><th>Beneficiary</th><th></th></tr></thead>
<tbody>${roiRows}</tbody></table>
<h2>Reward (Ajit)</h2>
<p>Legs ₹${report.reward.leg1} / ₹${report.reward.leg2} / ₹${report.reward.leg3} · Total ₹${report.reward.total} · Level ${report.reward.level}</p>
<table><thead><tr><th>M</th><th>Status</th><th>Reward</th><th>Need total</th><th>Need L1/L2/L3</th><th>Remaining</th></tr></thead>
<tbody>${rewardRows}</tbody></table>
<h2>Screenshots</h2>
<table><thead><tr><th>Name</th><th></th><th>Missing</th></tr></thead>
<tbody>${shotRows || "<tr><td colspan=3>Pending</td></tr>"}</tbody></table>
</body></html>`;
  const file = path.join(OUT, "report.html");
  fs.writeFileSync(file, html);
  return file;
}

async function main() {
  if (!report.ok) {
    console.error("Backend verification failed — still capturing screenshots");
  }
  if (report.roi.buyer_roi_balance !== "0.00") {
    throw new Error(`Deepest buyer ROI wallet must be 0, got ${report.roi.buyer_roi_balance}`);
  }
  const reportHtml = writeHtmlReport();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto(`file://${reportHtml}`);
  await shot(page, "00-calculation-report");

  const ajit = report.logins.ajit;
  console.log("Login Ajit", ajit.id);
  await loginAssociate(page, ajit.id, ajit.password);
  await shot(page, "01-ajit-dashboard");
  await assertVisible(page, "01-ajit-dashboard", [
    report.tiles.referral_income,
    report.tiles.level_income,
    report.tiles.reward_income,
    report.head.id,
  ]);
  await assertNavHasReward(page, true);

  await page.goto(`${BASE}/income/referral`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/income\/referral/, { timeout: 20000 });
  await page.getByText(/Level \/ Referral Income|11,000/).first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(800);
  await shot(page, "02-ajit-sale-income");
  await assertVisible(page, "02-ajit-sale-income", [report.samples.sale_l1.visible, "55,000"]);
  await assertLevel1Table(page, "02-ajit-sale-income");

  await page.goto(`${BASE}/income/roi`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/income\/roi/, { timeout: 20000 });
  await page.waitForTimeout(1500);
  await shot(page, "03-ajit-roi-income");
  await assertVisible(page, "03-ajit-roi-income", ["550", "11,000", "110"]);
  await assertLevel1Table(page, "03-ajit-roi-income");

  await page.getByRole("link", { name: /Reward Income/i }).first().click();
  await page.waitForURL(/income\/reward/, { timeout: 20000 });
  await page.waitForTimeout(1500);
  await shot(page, "04-ajit-reward");
  await assertVisible(page, "04-ajit-reward", ["75,000", "1,50,000", "Achieved"]);

  await page.goto(`${BASE}/fund/wallets`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await shot(page, "05-ajit-wallets");
  await assertVisible(page, "05-ajit-wallets", ["1,23,200", "1,265", "1,05,000"]);

  await logout(page);
  const l1 = report.logins.l1_child;
  console.log("Login L1", l1.id);
  await loginAssociate(page, l1.id, l1.password);
  await shot(page, "06-l1-child");
  await page.goto(`${BASE}/income/referral`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  await shot(page, "06b-l1-sale-income");

  await logout(page);
  const deep = report.logins.deepest;
  console.log("Login deepest buyer", deep.id);
  await loginAssociate(page, deep.id, deep.password);
  await shot(page, "07-buyer-dashboard");
  const buyerBody = await page.locator("body").innerText();
  if (buyerBody.includes("2,200.00") && /ROI wallet|ROI Income/i.test(buyerBody) === false) {
    /* ignore */
  }
  if (report.wallets.buyer.roi !== "0.00") {
    throw new Error("Buyer ROI wallet must be 0.00");
  }

  await logout(page);
  await loginAssociate(page, ajit.id, ajit.password);
  await page.goto(`${BASE}/genealogy`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /List/i }).click();
  await page.getByText("JOYSMK25U01").first().waitFor({ timeout: 30000 });
  await shot(page, "08-genealogy-team");
  await assertVisible(page, "08-genealogy-team", [report.head.id, "JOYSMK25U01"]);

  await page.goto(`${BASE}/users/team`, { waitUntil: "domcontentloaded" });
  await page.getByText("JOYSMK25U15").first().waitFor({ timeout: 30000 });
  await shot(page, "08b-ajit-team");
  await assertVisible(page, "08b-ajit-team", ["JOYSMK25U01", "JOYSMK25U15", "JOYSMK25U25"]);

  await page.goto(`${BASE}/income/referral`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/income\/referral/, { timeout: 20000 });
  await page.getByText(/11,000/).first().waitFor({ timeout: 20000 });
  await shot(page, "09-sale-l1-11000");
  await assertVisible(page, "09-sale-l1-11000", ["11,000", "55,000"]);
  await assertLevel1Table(page, "09-sale-l1-11000");

  await page.goto(`${BASE}/income/roi`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/income\/roi/, { timeout: 20000 });
  await page.getByText(/110/).first().waitFor({ timeout: 20000 });
  await shot(page, "10-roi-l1-110");
  await assertVisible(page, "10-roi-l1-110", ["110", "2,200"]);
  await assertLevel1Table(page, "10-roi-l1-110");

  await logout(page);
  console.log("Login super admin");
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /^Staff$/i }).click();
  await page.locator("#email").fill("admin@joyclub.associate");
  await page.locator("#password").fill("admin123");
  const [staffLogin] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/auth/login/") && r.request().method() === "POST",
      { timeout: 30000 },
    ),
    page.getByRole("button", { name: /Sign in/i }).click(),
  ]);
  if (!staffLogin.ok()) {
    throw new Error(`Staff login failed (${staffLogin.status()}): ${(await staffLogin.text()).slice(0, 200)}`);
  }
  await page.waitForURL(/dashboard/, { timeout: 30000 });
  await page.waitForTimeout(1500);
  await shot(page, "11-super-admin-no-reward-nav");
  await assertNavHasReward(page, false);

  report.screenshots = shots;
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  writeHtmlReport();

  await browser.close();
  console.log("\nPlaywright done. Screenshots in", OUT);
  if (!report.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  fs.writeFileSync(
    path.join(OUT, "verification.json"),
    JSON.stringify({ ...report, screenshots: shots, playwright_error: String(err) }, null, 2),
  );
  process.exit(1);
});
