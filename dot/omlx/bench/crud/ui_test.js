// Usage: node ui_test.js <ui-url> <api-url> <screenshot-dir>
// Drives an unknown React CRUD UI by role and text, checks results via the API.
// Prints one JSON object: {list, create, toggle, edit, delete, errors[]}.
const { chromium } = require(process.env.PW_CORE || "playwright-core");
const [ui, api, shots] = process.argv.slice(2);

const j = (path, opts) => fetch(api + path, opts).then((r) => r.json());
const books = async () => {
  const b = await j("/api/books");
  return Array.isArray(b) ? b : b.books || b.data || [];
};
const find = async (t) => (await books()).find((b) => b.title === t);
const row = (page, text) => page.locator("tr", { hasText: text }).first();
const settle = (page) => page.waitForTimeout(800);

async function fillField(scope, re, value) {
  for (const loc of [scope.getByLabel(re), scope.getByPlaceholder(re), scope.locator(`input[name*="${re.source}" i]`)]) {
    if (await loc.count()) { await loc.first().fill(value); return true; }
  }
  return false;
}

(async () => {
  const out = { list: false, create: false, toggle: false, edit: false, delete: false, errors: [] };
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on("dialog", (d) => d.accept());
  page.on("pageerror", (e) => out.errors.push(String(e).slice(0, 300)));
  const step = async (name, fn) => {
    try { out[name] = !!(await fn()); } catch (e) { out.errors.push(`${name}: ${String(e).split("\n")[0].slice(0, 300)}`); }
    await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true }).catch(() => {});
  };

  for (const t of ["Seed Book", "Delete Me"]) {
    await j("/api/books", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: t, author: "Seed Author", year: 1999, read: false }) });
  }
  await page.goto(ui, { waitUntil: "networkidle", timeout: 30000 }).catch((e) => out.errors.push(String(e)));

  await step("list", async () => (await page.locator("table").count()) > 0 && (await row(page, "Seed Book").count()) > 0);

  await step("create", async () => {
    const ok = (await fillField(page, /title/i, "UI Title")) && (await fillField(page, /author/i, "UI Author"));
    if (!ok) throw new Error("no title/author inputs found");
    await fillField(page, /year/i, "2024");
    await page.getByRole("button", { name: /add|create|save|submit|new/i }).first().click();
    await settle(page);
    return (await find("UI Title")) && (await row(page, "UI Title").count()) > 0;
  });

  await step("toggle", async () => {
    const before = (await find("Seed Book")).read;
    const r = row(page, "Seed Book");
    const box = r.locator('input[type="checkbox"]');
    if (await box.count()) await box.first().click();
    else await r.getByRole("button", { name: /read|toggle|mark/i }).first().click();
    await settle(page);
    return Boolean((await find("Seed Book"))?.read) !== Boolean(before);
  });

  await step("edit", async () => {
    await row(page, "Seed Book").getByRole("button", { name: /edit/i }).first().click();
    await settle(page);
    let filled = false;
    for (const el of await page.locator("input").all()) {
      if ((await el.inputValue().catch(() => "")) === "Seed Book") { await el.fill("Edited Book"); filled = true; break; }
    }
    if (!filled) throw new Error("no input holding the current title after clicking Edit");
    await page.getByRole("button", { name: /save|update|submit/i }).first().click();
    await settle(page);
    return !!(await find("Edited Book"));
  });

  await step("delete", async () => {
    await row(page, "Delete Me").getByRole("button", { name: /delete|remove/i }).first().click();
    await settle(page);
    return !(await find("Delete Me")) && (await row(page, "Delete Me").count()) === 0;
  });

  await browser.close();
  console.log(JSON.stringify(out));
})();
