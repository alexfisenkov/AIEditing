// Run this in the page you are capturing, through the browser pane's "run JavaScript" tool, one page per call.
// Replace __NAME__ (latin file name, e.g. home), __PORT__ and __TOKEN__ (printed by capture-receiver.mjs).
// It waits until the page has content, takes a copy of the markup without scripts and sends it to the
// local receiver by navigating to http://127.0.0.1:__PORT__/ with the data in the #fragment.
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 50; i++) {
  const text = (document.querySelector("main") || document.body).innerText || "";
  if (text.length > 200 && !/Loading|Checking sign-in|Загружаем/.test(text)) break; // wait out skeletons
  await wait(500);
}
await wait(500);
const raw = document.documentElement.cloneNode(true);
raw.querySelectorAll(
  "script,noscript,link[rel=modulepreload],link[rel=preload],link[rel=manifest],meta[http-equiv],input[type=hidden],meta[name*=csrf i],meta[name*=token i]"
).forEach((e) => e.remove());
const html = "<!doctype html>" + raw.outerHTML;
const gz = await new Response(new Blob([new TextEncoder().encode(html)]).stream().pipeThrough(new CompressionStream("gzip"))).arrayBuffer();
const bytes = new Uint8Array(gz);
let bin = "";
for (let i = 0; i < bytes.length; i += 8192) bin += String.fromCharCode(...bytes.subarray(i, i + 8192));
const b64 = btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
setTimeout(() => { location.href = "http://127.0.0.1:__PORT__/#__NAME__|__TOKEN__|" + b64; }, 60);
b64.length;
