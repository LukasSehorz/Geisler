/* ==========================================================================
   Galerie – balanced masonry grid, animated filter (hash synced), lightbox
   ========================================================================== */
(function () {
  "use strict";

  const grid = document.querySelector("[data-gallery-grid]");
  if (!grid || typeof window.gsap === "undefined") return;

  const gsap = window.gsap;
  const html = document.documentElement;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const section = document.querySelector("[data-gallery]");
  const filter = document.querySelector("[data-gallery-filter]");
  const track = filter ? filter.querySelector(".gfilter__track") : null;
  const indicator = filter ? filter.querySelector(".gfilter__indicator") : null;
  const chips = filter ? Array.from(filter.querySelectorAll("[data-filter]")) : [];
  const status = document.querySelector("[data-gallery-status]");
  const names = {};
  chips.forEach((c) => { names[c.dataset.filter] = c.dataset.name; });
  const refresh = () => { if (window.ScrollTrigger) window.ScrollTrigger.refresh(); };
  const headerH = () => parseFloat(getComputedStyle(html).getPropertyValue("--header-h")) || 80;

  const items = Array.from(grid.querySelectorAll(".gitem")).map((el) => {
    const img = el.querySelector("img");
    const it = {
      el, img,
      inner: el.querySelector(".gitem__inner"),
      cat: el.dataset.cat,
      w: parseFloat(img.getAttribute("width")) || 4,
      h: parseFloat(img.getAttribute("height")) || 3,
      fx: parseFloat(el.dataset.fx) || 0.5,
      fy: parseFloat(el.dataset.fy) || 0.5,
      full: el.dataset.full,
      alt: el.getAttribute("aria-label") || img.alt,
      revealed: false,
    };
    el.__item = it;
    return it;
  });

  /* ------------------------------------------------------------ masonry layout */
  const state = new Map();
  let visible = items.slice();
  let active = "all";
  let lastWidth = 0;
  let lastCols = 0;

  function metrics() {
    const cs = getComputedStyle(grid);
    return {
      cols: Math.max(1, parseInt(cs.getPropertyValue("--cols"), 10) || 3),
      gap: parseFloat(cs.getPropertyValue("--gap")) || 20,
      width: grid.clientWidth,
    };
  }

  // masonry: shortest-column placement, then balance column heights so the grid
  // ends on one clean line (small, focus-aware crops). Returns null if balancing
  // would need crops that are too strong.
  function masonry(list, cols, gap, colW) {
    const columns = Array.from({ length: cols }, () => ({ entries: [], h: 0 }));
    list.forEach((it) => {
      let best = 0;
      for (let c = 1; c < cols; c++) if (columns[c].h < columns[best].h - 2) best = c;
      const h = (colW * it.h) / it.w;
      columns[best].entries.push({ it, h });
      columns[best].h += h + gap;
    });

    if (cols > 1) {
      const totals = columns.map((c) => c.h - gap);
      const target = totals.reduce((a, b) => a + b, 0) / cols;
      const factors = columns.map((c) => {
        const gaps = gap * (c.entries.length - 1);
        return (target - gaps) / (c.h - gap - gaps);
      });
      if (!factors.every((f) => Math.abs(f - 1) <= 0.16)) return null;
      columns.forEach((c, k) => c.entries.forEach((e) => { e.h *= factors[k]; }));
    }

    const pos = new Map();
    let max = 0;
    columns.forEach((c, k) => {
      const x0 = Math.round(k * (colW + gap));
      const x1 = Math.round(k * (colW + gap) + colW);
      let y = 0;
      c.entries.forEach((e) => {
        const top = Math.round(y);
        const bottom = Math.round(y + e.h);
        pos.set(e.it, { x: x0, y: top, w: x1 - x0, h: bottom - top });
        y += e.h + gap;
      });
      if (c.entries.length) max = Math.max(max, Math.round(y - gap));
    });
    return { pos, height: max };
  }

  // justified rows for small sets: every row shares one height and spans the full
  // width, so natural aspect ratios are kept without any cropping
  function justifiedRows(list, cols, gap, width, colW) {
    const pos = new Map();
    const n = list.length;
    const nRows = Math.ceil(n / cols);
    const base = Math.floor(n / nRows);
    const extra = n % nRows;
    // rows keep full width (clean edges); only cap extreme heights on short viewports
    const maxH = Math.max(colW * 1.2, window.innerHeight * 0.8);
    let i = 0;
    let y = 0;
    for (let r = 0; r < nRows; r++) {
      const row = list.slice(i, i + base + (r < extra ? 1 : 0));
      i += row.length;
      const sumAr = row.reduce((a, it) => a + it.w / it.h, 0);
      let h = (width - gap * (row.length - 1)) / sumAr;
      let x = 0;
      if (h > maxH) {
        h = maxH;
        x = (width - (h * sumAr + gap * (row.length - 1))) / 2;
      }
      const top = Math.round(y);
      const bottom = Math.round(y + h);
      row.forEach((it) => {
        const w = h * (it.w / it.h);
        const left = Math.round(x);
        pos.set(it, { x: left, y: top, w: Math.round(x + w) - left, h: bottom - top });
        x += w + gap;
      });
      y += h + gap;
    }
    return { pos, height: Math.max(0, Math.round(y - gap)) };
  }

  function compute(list) {
    const { cols, gap, width } = metrics();
    const colW = (width - gap * (cols - 1)) / cols;
    let res = null;
    if (cols === 1) res = masonry(list, 1, gap, colW);
    else if (list.length >= cols * 2) res = masonry(list, cols, gap, colW);
    if (!res) res = justifiedRows(list, cols, gap, width, colW);
    lastWidth = width;
    lastCols = cols;
    return res;
  }

  let pendingHide = [];
  function apply(layout, animate) {
    const anim = animate && !reduce;
    const enter = [];
    const leave = [];
    pendingHide = [];

    items.forEach((it) => {
      const p = layout.pos.get(it);
      const was = state.get(it);
      if (p) {
        state.set(it, p);
        if (!anim) {
          gsap.killTweensOf(it.el);
          it.el.hidden = false;
          gsap.set(it.el, { x: p.x, y: p.y, width: p.w, height: p.h, autoAlpha: 1, scale: 1 });
        } else if (!was) {
          gsap.killTweensOf(it.el);
          it.el.hidden = false;
          gsap.set(it.el, { x: p.x, y: p.y, width: p.w, height: p.h, autoAlpha: 0, scale: 0.94 });
          enter.push(it.el);
        } else {
          gsap.to(it.el, { x: p.x, y: p.y, width: p.w, height: p.h, autoAlpha: 1, scale: 1, duration: 0.95, ease: "power3.inOut", overwrite: true });
        }
      } else if (was) {
        state.delete(it);
        if (!anim) { gsap.killTweensOf(it.el); it.el.hidden = true; }
        else leave.push(it);
      } else if (!anim) {
        it.el.hidden = true;
      }
    });

    if (!anim) {
      gsap.killTweensOf(grid);
      gsap.set(grid, { height: layout.height });
      return;
    }

    if (leave.length) {
      gsap.to(leave.map((it) => it.el), {
        autoAlpha: 0, scale: 0.94, duration: 0.45, ease: "power2.in", overwrite: true,
        onComplete: () => leave.forEach((it) => { if (!state.has(it)) it.el.hidden = true; }),
      });
    }
    if (enter.length) {
      gsap.to(enter, {
        autoAlpha: 1, scale: 1, duration: 0.85, ease: "power3.out", delay: 0.38, overwrite: true,
        stagger: { amount: Math.min(0.5, enter.length * 0.035) },
      });
    }
    gsap.to(grid, { height: layout.height, duration: 0.95, ease: "power3.inOut", overwrite: true, onComplete: refresh });
  }

  /* ------------------------------------------------------------ filter */
  function updateOverflow() {
    if (!track) return;
    const max = track.scrollWidth - track.clientWidth;
    const over = max > 2;
    track.classList.toggle("is-overflow", over);
    track.classList.toggle("at-start", !over || track.scrollLeft <= 2);
    track.classList.toggle("at-end", !over || track.scrollLeft >= max - 2);
    // let the wheel scroll the chips sideways instead of Lenis grabbing it
    if (over) track.setAttribute("data-lenis-prevent", "");
    else track.removeAttribute("data-lenis-prevent");
  }
  if (track) {
    track.addEventListener("scroll", updateOverflow, { passive: true });
    track.addEventListener("wheel", (e) => {
      if (!track.classList.contains("is-overflow") || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      const max = track.scrollWidth - track.clientWidth;
      const next = Math.max(0, Math.min(max, track.scrollLeft + e.deltaY));
      if (next === track.scrollLeft) return;
      e.preventDefault();
      track.scrollLeft = next;
    }, { passive: false });
  }

  function moveIndicator(animate) {
    updateOverflow();
    const btn = chips.find((c) => c.dataset.filter === active);
    if (!btn || !indicator) return;
    const props = { x: btn.offsetLeft, width: btn.offsetWidth };
    if (animate && !reduce) gsap.to(indicator, { ...props, duration: 0.75, ease: "power3.inOut", overwrite: true });
    else gsap.set(indicator, props);
    if (track && track.scrollWidth > track.clientWidth + 2) {
      const left = btn.offsetLeft - (track.clientWidth - btn.offsetWidth) / 2;
      track.scrollTo({ left: Math.max(0, left), behavior: animate && !reduce ? "smooth" : "auto" });
    }
  }

  function revealAll() {
    revealTriggers.forEach((t) => t.kill());
    revealTriggers = [];
    const rest = items.filter((it) => !it.revealed);
    rest.forEach((it) => { it.revealed = true; });
    if (rest.length) gsap.set(rest.map((it) => it.inner), { autoAlpha: 1, y: 0, overwrite: true });
  }

  function scrollToGrid(always) {
    if (!section) return;
    const rect = section.getBoundingClientRect();
    if (!always && rect.top > -40 && rect.top < window.innerHeight * 0.5) return;
    const y = Math.max(0, window.scrollY + rect.top - headerH() - 14);
    const lenis = window.__lenis;
    if (lenis) lenis.scrollTo(y, { duration: 1.3 });
    else window.scrollTo({ top: y, behavior: reduce ? "auto" : "smooth" });
  }

  function setFilter(key, opts = {}) {
    if (key !== "all" && !names[key]) key = "all";
    const changed = key !== active || opts.force;
    active = key;
    chips.forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.filter === key)));
    moveIndicator(opts.animate);
    if (changed) {
      if (opts.animate) revealAll();
      visible = items.filter((it) => key === "all" || it.cat === key);
      apply(compute(visible), opts.animate);
    }
    if (status) status.textContent = `${visible.length} Bilder${key === "all" ? "" : " – " + names[key]}`;
    if (opts.hash) {
      const url = key === "all" ? location.pathname + location.search : `#${key}`;
      history.replaceState(null, "", url);
    }
    if (opts.scroll) scrollToGrid(opts.scroll === "always");
  }

  const hashKey = () => {
    try { return decodeURIComponent(location.hash.replace(/^#/, "")); } catch (e) { return ""; }
  };

  // initial layout (before first scroll reveal) – pre-select filter from hash
  grid.classList.add("is-masonry");
  const initialKey = names[hashKey()] && hashKey() !== "all" ? hashKey() : "all";
  setFilter(initialKey, { force: true });
  if (filter) {
    filter.classList.add("is-ready");
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => moveIndicator(false));
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      if (chip.dataset.filter === active) return;
      setFilter(chip.dataset.filter, { animate: true, hash: true, scroll: true });
    });
  });

  window.addEventListener("hashchange", () => {
    const key = hashKey();
    if (names[key]) setFilter(key, { animate: true, scroll: "always" });
  });

  // in-page links such as <a href="#gaerten" data-gallery-link>
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href*='#']");
    if (!a || e.defaultPrevented) return;
    let url;
    try { url = new URL(a.href, location.href); } catch (err) { return; }
    if (url.pathname !== location.pathname) return;
    const key = decodeURIComponent(url.hash.slice(1));
    if (!names[key]) return;
    e.preventDefault();
    e.stopPropagation();
    setFilter(key, { animate: true, hash: true, scroll: "always" });
  }, true);

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const m = metrics();
      moveIndicator(false);
      if (m.width === lastWidth && m.cols === lastCols) return;
      apply(compute(visible), false);
      refresh();
    }, 120);
  });

  /* ------------------------------------------------------------ scroll reveal */
  let revealTriggers = [];
  if (!reduce) gsap.set(items.map((it) => it.inner), { autoAlpha: 0, y: 60 });

  document.addEventListener("site:ready", (e) => {
    const ST = (e.detail && e.detail.ScrollTrigger) || window.ScrollTrigger;
    if (!reduce && ST && ST.batch) {
      const pending = items.filter((it) => !it.revealed).map((it) => it.inner);
      revealTriggers = ST.batch(pending, {
        start: "top 94%",
        once: true,
        onEnter: (batch) => {
          batch.forEach((el) => { el.parentElement.__item.revealed = true; });
          gsap.to(batch, { autoAlpha: 1, y: 0, duration: 1.2, ease: "power3.out", stagger: 0.09, overwrite: true });
        },
      });
    } else {
      revealAll();
    }
    if (initialKey !== "all") setTimeout(() => scrollToGrid(true), 450);
  });

  /* ------------------------------------------------------------ lightbox */
  const lb = document.querySelector("[data-lightbox]");
  if (!lb) return;
  const backdrop = lb.querySelector(".lightbox__backdrop");
  const stage = lb.querySelector("[data-lb-stage]");
  const layers = Array.from(lb.querySelectorAll(".lightbox__img"));
  const chrome = Array.from(lb.querySelectorAll("[data-lb-chrome]"));
  const countEl = lb.querySelector("[data-lb-count]");
  const catEl = lb.querySelector("[data-lb-cat]");
  const altEl = lb.querySelector("[data-lb-alt]");
  const btnClose = lb.querySelector("[data-lb-close]");
  const btnPrev = lb.querySelector("[data-lb-prev]");
  const btnNext = lb.querySelector("[data-lb-next]");

  const pad = (n) => String(n).padStart(2, "0");
  const abs = (u) => { try { return new URL(u, location.href).href; } catch (e) { return u; } };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const loads = new Map();
  const loaded = new Set();

  let list = [];
  let index = 0;
  let front = 0;
  let isOpen = false;
  let closing = false;
  let token = 0;
  let lifted = null;

  function largestCandidate(img) {
    const set = img.getAttribute("srcset") || "";
    let best = img.getAttribute("src");
    let bw = 0;
    set.split(",").forEach((part) => {
      const [u, d] = part.trim().split(/\s+/);
      const w = parseInt(d, 10) || 0;
      if (u && w > bw) { bw = w; best = u; }
    });
    return best;
  }
  function srcFor(it) {
    const need = window.innerWidth * Math.min(window.devicePixelRatio || 1, 2);
    return abs(need <= 1250 || !it.full ? largestCandidate(it.img) : it.full);
  }
  function thumbSrc(it) {
    return it.img.complete && it.img.naturalWidth ? it.img.currentSrc || it.img.src : "";
  }
  function preload(url) {
    if (loads.has(url)) return loads.get(url);
    const im = new Image();
    im.decoding = "async";
    im.src = url;
    const p = (im.decode ? im.decode() : new Promise((res, rej) => { im.onload = res; im.onerror = rej; }))
      .then(() => { loaded.add(url); })
      .catch(() => { loads.delete(url); });
    loads.set(url, p);
    return p;
  }
  function preloadNeighbours() {
    if (list.length < 2) return;
    [1, -1].forEach((d) => preload(srcFor(list[(index + d + list.length) % list.length])));
  }

  function lift(it) {
    if (lifted && lifted !== it) lifted.el.classList.remove("is-lifted");
    lifted = it;
    if (it) it.el.classList.add("is-lifted");
  }

  // rect of the contained (object-fit: contain) image inside the stage
  function visualRect(it) {
    const sr = stage.getBoundingClientRect();
    const ar = it.w / it.h;
    let w = sr.width;
    let h = w / ar;
    if (h > sr.height) { h = sr.height; w = h * ar; }
    return { sr, left: sr.left + (sr.width - w) / 2, top: sr.top + (sr.height - h) / 2, width: w, height: h };
  }

  // transform + clip that makes the lightbox image sit exactly on the grid thumbnail
  function flipState(it) {
    const vr = visualRect(it);
    const sr = vr.sr;
    const tr = it.inner.getBoundingClientRect();
    let hs = 1;
    try { hs = new DOMMatrixReadOnly(getComputedStyle(it.img).transform).a || 1; } catch (e) { hs = 1; }
    const cover = Math.max(tr.width / vr.width, tr.height / vr.height);
    const cw = tr.width / cover;
    const ch = tr.height / cover;
    let l = vr.left - sr.left + (vr.width - cw) * it.fx;
    let t = vr.top - sr.top + (vr.height - ch) * it.fy;
    const vw = cw / hs;
    const vh = ch / hs;
    l += (cw - vw) / 2;
    t += (ch - vh) / 2;
    const s = cover * hs;
    const r = sr.width - l - vw;
    const b = sr.height - t - vh;
    const ox = sr.width / 2;
    const oy = sr.height / 2;
    const cx = l + vw / 2;
    const cy = t + vh / 2;
    const x = tr.left + tr.width / 2 - (sr.left + ox + s * (cx - ox));
    const y = tr.top + tr.height / 2 - (sr.top + oy + s * (cy - oy));
    const f = (n) => `${Math.max(0, n).toFixed(2)}px`;
    return {
      x, y, scale: s,
      clip: `inset(${f(t)} ${f(r)} ${f(b)} ${f(l)} round ${(5 / s).toFixed(2)}px)`,
      open: `inset(${f(vr.top - sr.top)} ${f(sr.right - vr.left - vr.width)} ${f(sr.bottom - vr.top - vr.height)} ${f(vr.left - sr.left)} round 0.00px)`,
      inView: tr.bottom > 0 && tr.top < window.innerHeight && tr.width > 0,
    };
  }

  function updateMeta(it, animate) {
    countEl.textContent = `${pad(index + 1)} / ${pad(list.length)}`;
    catEl.textContent = names[it.cat] || "";
    altEl.textContent = it.alt;
    if (animate && !reduce) gsap.fromTo([catEl, altEl], { autoAlpha: 0, y: 8 }, { autoAlpha: 1, y: 0, duration: 0.6, ease: "power3.out", stagger: 0.05, overwrite: true });
    const single = list.length < 2;
    btnPrev.hidden = single;
    btnNext.hidden = single;
  }

  function upgrade(it, layer, my) {
    const full = srcFor(it);
    if (abs(layer.src) === full) return;
    preload(full).then(() => {
      if (my === token && isOpen && layers[front] === layer && loaded.has(full)) layer.src = full;
    });
  }

  function open(it) {
    if (isOpen || closing) return;
    list = visible.slice();
    index = list.indexOf(it);
    if (index < 0) return;
    isOpen = true;
    const my = ++token;
    lb.hidden = false;
    html.classList.add("lightbox-open");
    if (window.__lenis) window.__lenis.stop();
    else html.style.overflow = "hidden";
    const cta = document.querySelector(".cursor-cta");
    if (cta) cta.classList.remove("cursor-cta--visible");

    front = 0;
    const img = layers[0];
    gsap.killTweensOf(layers);
    gsap.set(layers, { autoAlpha: 0, x: 0, y: 0, scale: 1, clearProps: "clipPath,zIndex" });
    const full = srcFor(it);
    img.src = loaded.has(full) ? full : thumbSrc(it) || full;
    img.alt = it.alt;
    updateMeta(it, false);

    const fs = flipState(it);
    if (!reduce && fs.inView) {
      lift(it);
      gsap.set(img, { autoAlpha: 1, x: fs.x, y: fs.y, scale: fs.scale, clipPath: fs.clip, zIndex: 2 });
      gsap.to(img, { x: 0, y: 0, scale: 1, clipPath: fs.open, duration: 1, ease: "power3.inOut", onComplete: () => gsap.set(img, { clearProps: "clipPath" }) });
    } else {
      gsap.fromTo(img, { autoAlpha: 0, scale: 0.97 }, { autoAlpha: 1, scale: 1, duration: reduce ? 0 : 0.6, ease: "power2.out" });
    }
    gsap.fromTo(backdrop, { autoAlpha: 0 }, { autoAlpha: 1, duration: reduce ? 0 : 0.7, ease: "power2.out" });
    // opacity only (no visibility toggling) so the close button can take focus right away
    gsap.fromTo(chrome, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: reduce ? 0 : 0.7, delay: reduce ? 0 : 0.5, ease: "power3.out", stagger: 0.05 });
    upgrade(it, img, my);
    preloadNeighbours();
    btnClose.focus({ preventScroll: true });
  }

  function go(dir) {
    if (!isOpen || list.length < 2) return;
    const next = (index + dir + list.length) % list.length;
    index = next;
    const it = list[next];
    const my = ++token;
    updateMeta(it, true);
    const out = layers[front];
    const inc = layers[1 - front];
    gsap.killTweensOf(inc);
    gsap.set(inc, { autoAlpha: 0, clearProps: "clipPath" });
    const full = srcFor(it);
    inc.src = loaded.has(full) ? full : thumbSrc(it) || full;
    inc.alt = it.alt;
    const ready = inc.decode ? inc.decode().catch(() => {}) : Promise.resolve();
    Promise.race([ready, wait(900)]).then(() => {
      if (my !== token || !isOpen) return;
      front = 1 - front;
      const d = reduce ? 0 : 1;
      gsap.killTweensOf(out);
      gsap.set(out, { zIndex: 1, clearProps: "clipPath" });
      gsap.to(out, { autoAlpha: 0, x: `+=${-70 * dir}`, scale: 1, y: 0, duration: 0.65 * d, ease: "power2.inOut" });
      gsap.fromTo(inc, { autoAlpha: 0, x: 70 * dir, y: 0, scale: 1, zIndex: 2 }, { autoAlpha: 1, x: 0, duration: 0.85 * d, ease: "power3.out" });
      upgrade(it, inc, my);
    });
    preloadNeighbours();
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    closing = true;
    token++;
    const it = list[index];
    const img = layers[front];
    const other = layers[1 - front];
    gsap.killTweensOf(layers);
    gsap.killTweensOf([backdrop, catEl, altEl]);
    gsap.set(other, { autoAlpha: 0 });

    // bring the current thumbnail into view behind the (opaque) backdrop
    let tr = it.inner.getBoundingClientRect();
    const topLimit = headerH();
    if (tr.top < topLimit || tr.bottom > window.innerHeight) {
      const y = window.scrollY + tr.top - Math.max(topLimit, (window.innerHeight - tr.height) / 2);
      if (window.__lenis) window.__lenis.scrollTo(Math.max(0, y), { immediate: true, force: true });
      else window.scrollTo(0, Math.max(0, y));
    }

    const d = reduce ? 0 : 1;
    const done = () => {
      lb.hidden = true;
      closing = false;
      lift(null);
      gsap.set(layers, { clearProps: "all" });
      layers.forEach((l) => { l.removeAttribute("src"); });
      html.classList.remove("lightbox-open");
      if (window.__lenis) window.__lenis.start();
      else html.style.overflow = "";
      it.el.focus({ preventScroll: true });
      refresh();
    };

    gsap.to(chrome, { opacity: 0, duration: 0.3 * d, ease: "power2.out" });
    gsap.to(backdrop, { autoAlpha: 0, duration: 0.75 * d, delay: 0.12 * d, ease: "power2.inOut" });
    const fs = flipState(it);
    if (!reduce && fs.inView && !it.el.hidden) {
      lift(it);
      gsap.set(img, { clipPath: fs.open, zIndex: 2 });
      gsap.to(img, { x: fs.x, y: fs.y, scale: fs.scale, clipPath: fs.clip, autoAlpha: 1, duration: 0.85, ease: "power3.inOut", onComplete: done });
    } else {
      gsap.to(img, { autoAlpha: 0, scale: 0.97, duration: 0.45 * d, ease: "power2.in", onComplete: done });
    }
  }

  grid.addEventListener("click", (e) => {
    const btn = e.target.closest(".gitem");
    if (btn && btn.__item) open(btn.__item);
  });
  btnClose.addEventListener("click", close);
  btnPrev.addEventListener("click", () => go(-1));
  btnNext.addEventListener("click", () => go(1));

  document.addEventListener("keydown", (e) => {
    if (!isOpen) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    else if (e.key === "Tab") {
      const focusables = [btnClose, btnPrev, btnNext].filter((b) => !b.hidden);
      const i = focusables.indexOf(document.activeElement);
      e.preventDefault();
      const n = e.shiftKey ? (i <= 0 ? focusables.length - 1 : i - 1) : (i + 1) % focusables.length;
      focusables[n].focus();
    }
  });

  // swipe / drag, tap outside the image closes
  let ptr = null;
  stage.addEventListener("pointerdown", (e) => {
    if (!isOpen || (e.pointerType === "mouse" && e.button !== 0)) return;
    ptr = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), axis: null };
    try { stage.setPointerCapture(e.pointerId); } catch (err) { /* noop */ }
  });
  stage.addEventListener("pointermove", (e) => {
    if (!ptr || e.pointerId !== ptr.id) return;
    const dx = e.clientX - ptr.x;
    const dy = e.clientY - ptr.y;
    if (!ptr.axis && Math.hypot(dx, dy) > 8) ptr.axis = Math.abs(dx) >= Math.abs(dy) ? "x" : "y";
    const img = layers[front];
    if (ptr.axis === "x") {
      gsap.set(img, { x: dx * (list.length < 2 ? 0.25 : 1) });
    } else if (ptr.axis === "y") {
      const p = Math.min(Math.max(dy, 0) / window.innerHeight, 0.5);
      gsap.set(img, { y: dy > 0 ? dy : dy * 0.2, scale: 1 - p * 0.35 });
      gsap.set(backdrop, { autoAlpha: 1 - p * 1.2 });
    }
  });
  const endPointer = (e) => {
    if (!ptr || e.pointerId !== ptr.id) return;
    const s = ptr;
    ptr = null;
    const dx = e.clientX - s.x;
    const dy = e.clientY - s.y;
    const v = Math.abs(dx) / Math.max(1, performance.now() - s.t);
    if (e.type !== "pointercancel") {
      if (s.axis === "x" && list.length > 1 && (Math.abs(dx) > 70 || (v > 0.45 && Math.abs(dx) > 24))) { go(dx < 0 ? 1 : -1); return; }
      if (s.axis === "y" && dy > 110) { close(); return; }
      if (!s.axis) {
        const vr = visualRect(list[index]);
        const inside = e.clientX >= vr.left && e.clientX <= vr.left + vr.width && e.clientY >= vr.top && e.clientY <= vr.top + vr.height;
        if (!inside) { close(); return; }
      }
    }
    gsap.to(layers[front], { x: 0, y: 0, scale: 1, duration: 0.55, ease: "power3.out" });
    gsap.to(backdrop, { autoAlpha: 1, duration: 0.4 });
  };
  stage.addEventListener("pointerup", endPointer);
  stage.addEventListener("pointercancel", endPointer);
  // clicks on the empty bar / caption area also close
  lb.addEventListener("click", (e) => {
    if (e.target === lb || e.target === backdrop || e.target.classList.contains("lightbox__bar") || e.target.classList.contains("lightbox__caption")) close();
  });
})();
