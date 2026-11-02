// Adds monochrome service logos to src/data/brands.json of a working folder, on request.
// The kit ships none: a brand mark is a trademark, and a licence for each icon is not confirmed. Take only the
// logos the speaker names, and read the brand's guidelines before the video is published.
//   node add-logos.mjs "<W>" claude telegram gemini=googlegemini
// The name is the slug in the simple-icons npm package (pinned below); "alias=slug" stores it under your own name.
// Nothing found for a slug: use a TextMark in the scene instead.
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const PACKAGE = "simple-icons@16.36.0";
const [, , W, ...items] = process.argv;
if (!W || !items.length) {
  console.error('Запуск: node add-logos.mjs "<рабочая папка>" <имя> [<имя>=<slug>...]');
  process.exit(2);
}
const file = join(W, "src/data/brands.json");
const brands = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};
const shell = process.platform === "win32";

const tmp = mkdtempSync(join(tmpdir(), "logos-"));
try {
  execFileSync("npm", ["pack", "--silent", "--pack-destination", tmp, PACKAGE], { stdio: "ignore", shell });
  const tgz = readdirSync(tmp).find((f) => f.endsWith(".tgz"));
  execFileSync("tar", ["-xzf", join(tmp, tgz), "-C", tmp]);
  for (const item of items) {
    const [alias, slug = alias] = item.split("=");
    const svg = join(tmp, "package/icons", `${slug}.svg`);
    if (!existsSync(svg)) {
      console.log(`нет в наборе: ${slug}`);
      continue;
    }
    const paths = [...readFileSync(svg, "utf8").matchAll(/\sd="([^"]+)"/g)].map((m) => m[1]);
    if (!paths.length) {
      console.log(`нет контура: ${slug}`);
      continue;
    }
    brands[alias] = paths.join(" ");
    console.log(`добавлен: ${alias}`);
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
writeFileSync(file, JSON.stringify(brands, null, 1) + "\n");
