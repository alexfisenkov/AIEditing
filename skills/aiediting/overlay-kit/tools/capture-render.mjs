// Renders captured page markup (from capture-receiver.mjs) into PNG screens at 2x: <name>-dark.png, <name>-light.png.
// No sign-in, no cookies: the page is replayed from the saved markup; public CSS and fonts are fetched from the
// site's own origin. Real Chrome is used (channel "chrome"), nothing is downloaded. Reads only, writes nothing to the site.
//
//   node capture-render.mjs --in <html dir> --out <png dir> --origin https://site.example \
//        [--themes dark,light] [--theme-attr data-theme] [--hide "css selector"]... [--rules rules.json] \
//        [--block "**/api/**"]... [--width 1600] [--max-height 7000] [name ...]
//
// What to cut is a parameter: --hide removes every element matching a CSS selector; --rules points at a JSON file
//   [{"selector": "div,aside", "text": "^\\s*Preview mode", "maxLength": 220}]
// that removes elements whose text matches (and is not longer than maxLength: so a page wrapper is never removed).
// Cut owner-only service blocks and anything that shows other people's personal data BEFORE the PNG is used.
import { chromium } from "playwright";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";

const argv = process.argv.slice(2);
const opts = { hide: [], block: [], names: [] };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (["--hide", "--block"].includes(a)) opts[a.slice(2)].push(argv[++i]);
  else if (a.startsWith("--")) opts[a.slice(2)] = argv[++i];
  else opts.names.push(a);
}
const need = (k) => {
  if (!opts[k]) {
    console.error(`Не задано --${k}. Запуск: node capture-render.mjs --in <html> --out <png> --origin https://сайт [--hide селектор] [--rules файл.json] [имена]`);
    process.exit(2);
  }
  return opts[k];
};
const SRC = need("in");
const OUT = need("out");
const ORIGIN = need("origin").replace(/\/+$/, "");
const THEMES = (opts.themes ?? "dark,light").split(",");
const THEME_ATTR = opts["theme-attr"] ?? "";
const WIDTH = Number(opts.width ?? 1600);
const MAX_CSS_H = Number(opts["max-height"] ?? 7000); // the screenshot limit is 16384 px at 2x
const BLOCK = opts.block.length ? opts.block : ["**/api/**", "**/video/**"];
const RULES = opts.rules ? JSON.parse(readFileSync(opts.rules, "utf8")) : [];

mkdirSync(OUT, { recursive: true });
const names = readdirSync(SRC)
  .filter((f) => f.endsWith(".html"))
  .map((f) => basename(f, ".html"))
  .filter((n) => !opts.names.length || opts.names.includes(n));
if (!names.length) {
  console.error("Нет страниц для рендера в " + SRC);
  process.exit(2);
}

// Runs inside the page
const CLEAN = ({ hide, rules }) => {
  hide.forEach((sel) => document.querySelectorAll(sel).forEach((e) => e.remove()));
  for (const r of rules) {
    const re = new RegExp(r.text);
    [...document.querySelectorAll(r.selector)]
      .filter((e) => re.test(e.textContent) && e.textContent.length <= (r.maxLength ?? 300))
      .forEach((e) => e.remove());
  }
  // A video does not play in a snapshot: a quiet graphite panel of the same shape keeps the layout
  document.querySelectorAll("video").forEach((v) => {
    const d = document.createElement("div");
    d.style.cssText = "width:100%;aspect-ratio:16/9;border-radius:15px;background:linear-gradient(165deg,#202123,#0E0E10);";
    v.replaceWith(d);
  });
};
const MEASURE = () => Math.max(...[...document.querySelectorAll("*")].map((e) => e.scrollHeight), document.documentElement.scrollHeight);

let browser;
try {
  browser = await chromium.launch({ channel: "chrome" });
} catch (err) {
  console.error("Не запускается установленный Google Chrome (скачивать ничего не нужно, нужен сам Chrome): " + String(err).split("\n")[0]);
  process.exit(2);
}
for (const theme of THEMES) {
  const ctx = await browser.newContext({ viewport: { width: WIDTH, height: 1000 }, deviceScaleFactor: 2, reducedMotion: "reduce", colorScheme: theme === "light" ? "light" : "dark" });
  for (const pattern of BLOCK) await ctx.route(pattern, (r) => r.abort());
  for (const n of names) {
    const page = await ctx.newPage();
    const html = readFileSync(join(SRC, `${n}.html`), "utf8");
    // Served from the site's own origin, otherwise cross-origin stylesheets are refused; the markup never goes to the network
    await page.route(`${ORIGIN}/__snapshot`, (r) => r.fulfill({ contentType: "text/html; charset=utf-8", body: html }));
    await page.goto(`${ORIGIN}/__snapshot`, { waitUntil: "networkidle", timeout: 60000 });
    if (THEME_ATTR) await page.evaluate(([a, t]) => document.documentElement.setAttribute(a, t), [THEME_ATTR, theme]);
    await page.evaluate(CLEAN, { hide: opts.hide, rules: RULES });
    await page.evaluate(() => document.fonts.ready);
    const h = Math.min(await page.evaluate(MEASURE), MAX_CSS_H);
    await page.setViewportSize({ width: WIDTH, height: Math.max(1000, h) });
    await page.waitForTimeout(500);
    await page.screenshot({ path: join(OUT, `${n}-${theme}.png`) });
    const text = await page.evaluate(() => (document.querySelector("main") ?? document.body).innerText.replace(/\s+/g, " ").slice(0, 100));
    console.log(n, theme, "height", h, "|", text);
    await page.close();
  }
  await ctx.close();
}
await browser.close();
writeFileSync(join(OUT, ".done"), new Date().toISOString());
