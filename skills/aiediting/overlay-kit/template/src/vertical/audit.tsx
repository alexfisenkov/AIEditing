// The audit of one frame. It writes to the browser console, `overlay.py vertical-check` reads it: text inside SAFE and not
// smaller than MIN_TEXT; nothing lies on anything else (text, plates, pictures, the face, the circle and the band of the speaker);
// neighbours keep a gap; the stage is not left empty. Text inside real screens is a picture: only the eye checks it.
// The names of the findings are the vocabulary of the report the person reads.
import React, { useLayoutEffect, useRef } from "react";
import { useCurrentFrame } from "remotion";
import { MIN_TEXT, SAFE, SMALL_OK } from "./safe";
import { Box, TIGHT, area, crossing, distance } from "./geometry";

type Item = { el: HTMLElement; box: Box; name: string };

const VISIBLE = 0.3; // less opaque than this is not on the screen yet
const SETTLED = 0.9; // the gap is measured only for what has settled

const seen = (el: HTMLElement) => {
  let o = 1;
  for (let e: HTMLElement | null = el; e; e = e.parentElement) {
    const s = getComputedStyle(e);
    if (s.visibility === "hidden" || s.display === "none") return 0;
    o *= Number(s.opacity);
  }
  return o;
};

export const auditFrame = (root: HTMLElement): string[] => {
  const o = root.getBoundingClientRect();
  const rel = (r: DOMRect): Box => ({ left: r.left - o.left, right: r.right - o.left, top: r.top - o.top, bottom: r.bottom - o.top });
  // While the call to action stands, its curtain hides the scene: the scene is not audited, the card is (zone, size, overlaps).
  // The speaker's circle above the curtain and the empty-stage check belong to the scene, so they are skipped too.
  const curtain = !!root.querySelector("[data-cta]");
  const scope: HTMLElement | null = curtain ? root.querySelector<HTMLElement>("[data-cta-card]") : root;
  if (!scope) return [];
  const bad: string[] = [];
  const range = document.createRange();
  const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
  const texts: { text: string; el: HTMLElement; box: Box }[] = [];
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = (n.textContent ?? "").trim();
    const el = n.parentElement;
    if (!text || !el || el.closest("[data-outside]") || seen(el) < VISIBLE) continue;
    range.selectNodeContents(n);
    const r = range.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const box = rel(r);
    texts.push({ text: text.slice(0, 26), el, box });
    if (box.left < SAFE.x0 - 1 || box.right > SAFE.x1 + 1 || box.top < SAFE.y0 - 1 || box.bottom > SAFE.y1 + 1) bad.push(`ЗОНА «${text.slice(0, 26)}»`);
    const small = parseFloat(getComputedStyle(el).fontSize) < MIN_TEXT && !el.closest("[data-small-ok]") && !SMALL_OK.includes(text);
    if (small) bad.push(`МЕЛКО «${text.slice(0, 26)}»`);
  }
  const plates: Item[] = [];
  const pictures: Item[] = [];
  // The visible part: a picture inside a window with overflow hidden counts only as far as the window shows it
  const visibleBox = (el: HTMLElement): Box => {
    let b = rel(el.getBoundingClientRect());
    for (let e = el.parentElement; e && e !== root; e = e.parentElement) {
      if (getComputedStyle(e).overflow === "visible") continue;
      const c = rel(e.getBoundingClientRect());
      b = { left: Math.max(b.left, c.left), right: Math.min(b.right, c.right), top: Math.max(b.top, c.top), bottom: Math.min(b.bottom, c.bottom) };
    }
    return b;
  };
  const all = Array.from(scope.querySelectorAll<HTMLElement>("*"));
  if (curtain) all.unshift(scope); // the card is a plate itself
  all.forEach((el) => {
    if (el.closest("[data-outside]") || seen(el) < VISIBLE) return;
    const box = visibleBox(el);
    if (box.right - box.left < 40 || box.bottom - box.top < 30) return;
    const s = getComputedStyle(el);
    if (el.tagName === "IMG" || el.tagName === "VIDEO" || el.tagName === "CANVAS") {
      pictures.push({ el, box, name: (el.getAttribute("src") ?? "").split("/").pop()?.slice(0, 22) || "картинка" });
    } else if (parseFloat(s.borderTopLeftRadius) > 0 && (s.backgroundImage !== "none" || !/rgba\(.*, 0\)|transparent/.test(s.backgroundColor))) {
      plates.push({ el, box, name: (el.textContent ?? "").trim().slice(0, 22) || "плашка" });
    }
  });
  for (let i = 0; i < texts.length; i++) {
    for (let j = i + 1; j < texts.length; j++) {
      const a = texts[i];
      const b = texts[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (crossing(a.box, b.box) > 0.08 * Math.min(area(a.box), area(b.box))) bad.push(`ТЕКСТ НА ТЕКСТЕ «${a.text}» × «${b.text}»`);
    }
    for (const p of plates) {
      if (!p.el.contains(texts[i].el) && crossing(texts[i].box, p.box) > 0.08 * area(texts[i].box)) bad.push(`ПЛАШКА НА ТЕКСТЕ «${p.name}» × «${texts[i].text}»`);
    }
    for (const p of pictures) {
      const home = texts[i].el.closest("[data-over-picture]");
      if (!home && crossing(texts[i].box, p.box) > 0.08 * area(texts[i].box)) bad.push(`ТЕКСТ НА КАРТИНКЕ ${p.name} × «${texts[i].text}»`);
    }
  }
  for (let i = 0; i < plates.length; i++) {
    for (let j = i + 1; j < plates.length; j++) {
      const a = plates[i];
      const b = plates[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (crossing(a.box, b.box) > 0.05 * Math.min(area(a.box), area(b.box))) bad.push(`ПЛАШКА НА ПЛАШКЕ «${a.name}» × «${b.name}»`);
    }
    for (const p of pictures) {
      if (plates[i].el.contains(p.el) || p.el.contains(plates[i].el)) continue;
      if (crossing(plates[i].box, p.box) > 0.08 * Math.min(area(plates[i].box), area(p.box))) bad.push(`ПЛАШКА НА КАРТИНКЕ «${plates[i].name}» × ${p.name}`);
    }
  }
  const page = root.ownerDocument;
  const speaker = (sel: string) => {
    const el = page.querySelector<HTMLElement>(sel);
    return el && Number(el.dataset.shown ?? 1) > VISIBLE ? rel(el.getBoundingClientRect()) : null;
  };
  const face = speaker("[data-face]");
  const ring = speaker("[data-ring]");
  const band = speaker("[data-band]");
  const onSpeaker = (name: string, box: Box) => {
    if (face && crossing(box, face) > 0.04 * area(box)) bad.push(`НА ЛИЦЕ «${name}»`);
    if (ring && crossing(box, ring) > 0.04 * area(box)) bad.push(`НА КРУЖКЕ «${name}»`);
    if (band && crossing(box, band) > 0.04 * area(box)) bad.push(`НА ВИДЕО СПИКЕРА «${name}»`);
  };
  if (!curtain) {
    texts.forEach((x) => onSpeaker(x.text, x.box));
    plates.forEach((x) => onSpeaker(x.name, x.box));
    pictures.forEach((x) => onSpeaker(x.name, x.box));
  }
  // Touching: the eye reads it as a collision although nothing overlaps. Only what has settled is measured.
  const settled = <T extends { el: HTMLElement }>(list: T[]) => list.filter((x) => seen(x.el) > SETTLED);
  const solid = [...settled(plates), ...settled(pictures)];
  for (let i = 0; i < solid.length; i++) {
    for (let j = i + 1; j < solid.length; j++) {
      const a = solid[i];
      const b = solid[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      if (distance(a.box, b.box) < TIGHT) bad.push(`ВПЛОТНУЮ «${a.name}» × «${b.name}»`);
    }
    for (const x of settled(texts)) {
      if (solid[i].el.contains(x.el) || x.el.closest("[data-over-picture]")) continue;
      if (distance(solid[i].box, x.box) < TIGHT) bad.push(`ВПЛОТНУЮ «${solid[i].name}» × «${x.text}»`);
    }
  }
  if (!curtain && !texts.length && !plates.length && !pictures.length) {
    if (ring) bad.push("ПУСТО кружок");
    else if (band) bad.push("ПУСТО полоса");
  }
  return Array.from(new Set(bad));
};

export const SafeAudit: React.FC<{ on: boolean; children: React.ReactNode }> = ({ on, children }) => {
  const root = useRef<HTMLDivElement>(null);
  const frame = useCurrentFrame();
  useLayoutEffect(() => {
    if (!on || !root.current) return;
    const bad = auditFrame(root.current);
    if (bad.length) console.log(`SAFE ${frame}|${bad.join("|")}`);
  });
  return (
    <div ref={root} style={{ position: "absolute", inset: 0 }}>
      {children}
    </div>
  );
};
