// Local receiver for page snapshots. Listens on 127.0.0.1 only.
// The page reaches it through the #fragment of a navigation (gzip + base64url): a fragment is not sent to any server,
// though the address can stay in the browser's history (see capture-guide.md), and the receiver's own page then POSTs
// it to this same process. A random token keeps other pages out.
//   node capture-receiver.mjs <out-dir> [--port 7791] [--token T]
import { createServer } from "node:http";
import { randomBytes } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { gunzipSync } from "node:zlib";

const args = process.argv.slice(2);
const flag = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
const OUT = args.find((a, i) => !a.startsWith("--") && !String(args[i - 1] ?? "").startsWith("--"));
if (!OUT) {
  console.error("Запуск: node capture-receiver.mjs <папка для html> [--port 7791] [--token T]");
  process.exit(2);
}
const PORT = Number(flag("--port", "7791"));
const TOKEN = flag("--token", randomBytes(8).toString("hex"));
const MAX_BYTES = 64 * 1024 * 1024;
mkdirSync(OUT, { recursive: true });

const RECV = `<!doctype html><meta charset=utf-8><title>receiver</title><body style="font:16px sans-serif">
<script>
const [name, token, b64] = location.hash.slice(1).split('|');
fetch('/save?name=' + encodeURIComponent(name) + '&token=' + encodeURIComponent(token), { method: 'POST', body: b64 })
  .then((r) => r.text())
  .then((t) => { document.body.textContent = t; document.title = 'ok ' + t; history.replaceState(null, '', '/'); });
</script>`;

createServer((req, res) => {
  // A browser page on another host must not be able to write here (DNS rebinding): only our own origin passes
  if (req.headers.host !== `127.0.0.1:${PORT}`) {
    res.statusCode = 403;
    return res.end("forbidden");
  }
  const url = new URL(req.url, "http://127.0.0.1");
  if (req.method === "GET") {
    res.setHeader("content-type", "text/html; charset=utf-8");
    return res.end(RECV);
  }
  if (req.method !== "POST" || url.pathname !== "/save" || url.searchParams.get("token") !== TOKEN) {
    res.statusCode = 403;
    return res.end("forbidden");
  }
  const chunks = [];
  let size = 0;
  req.on("data", (c) => {
    size += c.length;
    if (size > MAX_BYTES) req.destroy();
    else chunks.push(c);
  });
  req.on("end", () => {
    const name = (url.searchParams.get("name") ?? "").replace(/[^\p{L}\p{N}_-]/gu, "_").slice(0, 64) || "page";
    try {
      const raw = gunzipSync(Buffer.from(Buffer.concat(chunks).toString(), "base64url"));
      writeFileSync(join(OUT, `${name}.html`), raw);
      console.log("saved", `${name}.html`, raw.length);
      res.end(`saved ${name}.html ${raw.length}`);
    } catch {
      res.statusCode = 400;
      res.end("bad snapshot");
    }
  });
}).listen(PORT, "127.0.0.1", () => console.log(`listening on 127.0.0.1:${PORT}\nTOKEN ${TOKEN}`));
