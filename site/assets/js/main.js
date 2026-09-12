/* ==========================================================================
   Gartengestaltung Geißler – interactions & motion
   Lenis smooth scroll (lerp .14), GSAP ScrollTrigger + SplitText text reveal
   (blur/brightness/rotateX per char, scrubbed on scroll), cursor CTA,
   mega menus, page transition overlay, image reveals, sliders.
   ========================================================================== */
(function () {
  "use strict";

  window.__animReady = true;
  const html = document.documentElement;
  const body = document.body;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const hasGsap = typeof window.gsap !== "undefined";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  if (!hasGsap) {
    html.classList.add("reveal-fallback");
    html.classList.remove("is-entering");
    return;
  }

  gsap.registerPlugin(ScrollTrigger, SplitText);

  /* ------------------------------------------------------------ smooth scroll */
  let lenis = null;
  if (!reduce && typeof window.Lenis !== "undefined") {
    lenis = new Lenis({ lerp: 0.14 });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);
  }
  window.__lenis = lenis;

  const scrollTo = (target, opts = {}) => {
    if (lenis) lenis.scrollTo(target, { offset: -90, duration: 1.4, ...opts });
    else {
      const el = typeof target === "string" ? $(target) : target;
      if (el && el.scrollIntoView) el.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
    }
  };

  /* ------------------------------------------------------------ long German words: never break inside a word */
  const fitted = new Set();
  const fitWords = (el) => {
    el.style.fontSize = "";
    const words = el.querySelectorAll(".word");
    const avail = el.clientWidth;
    if (!words.length || !avail) return;
    let size = parseFloat(getComputedStyle(el).fontSize);
    const min = size * 0.55;
    const widest = () => Math.max(...Array.from(words, (w) => w.offsetWidth));
    let guard = 0;
    while (widest() > avail + 1 && size > min && guard++ < 14) {
      size *= 0.93;
      el.style.fontSize = size + "px";
    }
    fitted.add(el);
  };
  let fitTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(fitTimer);
    fitTimer = setTimeout(() => { fitted.forEach(fitWords); ScrollTrigger.refresh(); }, 250);
  });

  /* ------------------------------------------------------------ text reveal effect */
  gsap.registerEffect({
    name: "textReveal",
    effect: (target, config) => {
      const el = gsap.utils.toArray(target)[0];
      if (!el) return gsap.timeline();
      const split = new SplitText(el, { type: "words, chars", charsClass: "char", wordsClass: "word" });
      gsap.set(el, { visibility: "visible" });
      fitWords(el);
      const scrollTriggerParams = {
        trigger: el,
        scrub: 1,
        start: "top bottom-=15%",
        end: window.innerWidth < 1000 ? "bottom center+=5%" : "bottom center-=15%",
      };
      return gsap.to(split.chars, {
        duration: config.duration,
        opacity: 1,
        rotateX: 0,
        filter: "blur(0px) brightness(100%)",
        ease: "sine.out",
        stagger: !config.onScroll ? config.stagger : 0.1,
        scrollTrigger: config.onScroll ? scrollTriggerParams : null,
        onComplete: () => el.classList.add("reveal-done"),
      });
    },
    defaults: { duration: 2, stagger: { amount: 0.4, from: "random" }, onScroll: false },
    extendTimeline: true,
  });

  function scrubReveal() {
    $$("[data-scrub-reveal]").forEach((el) => {
      if (el.closest("[data-hero]")) return;
      const target = el.classList.contains("heading") || el.classList.contains("title") ? el : ($(".heading", el) || $(".title", el) || el);
      if (reduce) { gsap.set(target, { visibility: "visible" }); return; }
      gsap.effects.textReveal(target, { onScroll: true });
    });
  }

  /* ------------------------------------------------------------ page transition */
  function pageTransition() {
    const overlay = $(".transition");
    if (!overlay) return;
    gsap.fromTo(overlay, { autoAlpha: 1 }, {
      autoAlpha: 0, duration: 1.5, delay: 0.35, ease: "sine.out",
      onComplete: () => html.classList.remove("is-entering"),
    });
    document.addEventListener("click", (e) => {
      const a = e.target.closest("a[href]");
      if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (a.target === "_blank" || a.hasAttribute("download") || a.hasAttribute("data-no-transition")) return;
      const href = a.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return;
      let url;
      try { url = new URL(a.href, location.href); } catch (err) { return; }
      if (url.origin !== location.origin) return;
      if (url.pathname === location.pathname && url.hash) {
        e.preventDefault();
        scrollTo(url.hash);
        return;
      }
      e.preventDefault();
      closeMenus();
      gsap.to(overlay, { autoAlpha: 1, duration: 0.45, ease: "sine.inOut", onComplete: () => { location.href = a.href; } });
    });
    window.addEventListener("pageshow", (ev) => { if (ev.persisted) gsap.set(overlay, { autoAlpha: 0 }); });
  }

  /* ------------------------------------------------------------ header state */
  function headerState() {
    // header stays sticky at all times (as in the reference) – only switches to the solid state
    const update = (y) => {
      body.classList.toggle("is-scrolled", y > 40);
    };
    if (lenis) lenis.on("scroll", ({ scroll }) => update(scroll));
    else window.addEventListener("scroll", () => update(window.scrollY), { passive: true });
    update(window.scrollY);
  }

  /* ------------------------------------------------------------ mega menus */
  let closeMenus = () => {};
  function megaMenus() {
    const items = $$("[data-mega]");
    let openItem = null;
    let closeTimer = null;
    let openTimer = null;

    const hydrate = (item) => {
      if (item.dataset.hydrated) return;
      item.dataset.hydrated = "1";
      $$("img[data-defer-src]", item).forEach((img) => {
        img.srcset = img.getAttribute("data-defer-srcset");
        img.src = img.getAttribute("data-defer-src");
        img.removeAttribute("data-defer-src");
        img.removeAttribute("data-defer-srcset");
      });
    };
    const open = (item) => {
      hydrate(item);
      clearTimeout(closeTimer);
      if (openItem === item) return;
      if (openItem) close(openItem, true);
      openItem = item;
      item.classList.add("is-open");
      body.classList.add("mega-open");
      body.classList.remove("header-hidden");
      const toggle = $("[data-mega-toggle]", item);
      if (toggle) toggle.setAttribute("aria-expanded", "true");
      if (!reduce) gsap.fromTo($$(".mega__anim", item), { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 0.7, ease: "power3.out", stagger: 0.03, overwrite: true });
    };
    const close = (item) => {
      if (!item) return;
      item.classList.remove("is-open");
      const toggle = $("[data-mega-toggle]", item);
      if (toggle) toggle.setAttribute("aria-expanded", "false");
      if (openItem === item) openItem = null;
      if (!openItem) body.classList.remove("mega-open");
    };
    closeMenus = () => { items.forEach((i) => close(i)); body.classList.remove("menu-open"); };

    items.forEach((item) => {
      const toggle = $("[data-mega-toggle]", item);
      const imgs = $$(".mega__img", item);
      const links = $$("[data-mega-img]", item);
      item.addEventListener("mouseenter", () => {
        hydrate(item);
        if (!finePointer) return;
        clearTimeout(closeTimer);
        openTimer = setTimeout(() => open(item), openItem ? 0 : 90);
      });
      item.addEventListener("mouseleave", () => {
        clearTimeout(openTimer);
        closeTimer = setTimeout(() => close(item), 220);
      });
      if (toggle) {
        toggle.addEventListener("click", (e) => {
          if (!item.classList.contains("is-open") && !finePointer) { e.preventDefault(); open(item); }
        });
        toggle.addEventListener("focus", () => hydrate(item));
        toggle.addEventListener("keydown", (e) => {
          if (e.key === "ArrowDown" || e.key === " ") { e.preventDefault(); open(item); const first = $(".mega a", item); if (first) first.focus(); }
        });
      }
      item.addEventListener("focusout", (e) => { if (!item.contains(e.relatedTarget)) close(item); });
      links.forEach((link) => {
        const activate = () => {
          const idx = +link.dataset.megaImg;
          imgs.forEach((im, i) => im.classList.toggle("is-active", i === idx));
          links.forEach((l) => l.classList.toggle("is-active", l === link));
        };
        link.addEventListener("mouseenter", activate);
        link.addEventListener("focus", activate);
      });
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenus(); });
    const backdrop = $(".mega-backdrop");
    if (backdrop) backdrop.addEventListener("click", closeMenus);
  }

  /* ------------------------------------------------------------ mobile menu */
  function mobileMenu() {
    const toggle = $("[data-menu-toggle]");
    const menu = $("[data-mobile-menu]");
    if (!toggle || !menu) return;
    toggle.addEventListener("click", () => {
      const isOpen = body.classList.toggle("menu-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.setAttribute("aria-label", isOpen ? "Menü schließen" : "Menü öffnen");
      if (lenis) isOpen ? lenis.stop() : lenis.start();
      if (isOpen && !reduce) gsap.fromTo($$(".mobile-menu__list > li, .mobile-menu__contact", menu), { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: 0.6, stagger: 0.05, ease: "power3.out" });
    });
    $$("[data-sub-toggle]", menu).forEach((btn) => {
      btn.addEventListener("click", () => {
        const li = btn.closest(".mobile-menu__item");
        const isOpen = li.classList.toggle("is-open");
        btn.setAttribute("aria-expanded", String(isOpen));
      });
    });
  }

  /* ------------------------------------------------------------ cursor CTA */
  function cursor() {
    const dot = $(".cursor");
    const cta = $(".cursor-cta");
    if (!finePointer || !dot || !cta) return;
    const label = $(".cursor-cta__label", cta);
    const dx = gsap.quickTo(dot, "x", { duration: 0.18, ease: "power3" });
    const dy = gsap.quickTo(dot, "y", { duration: 0.18, ease: "power3" });
    const cx = gsap.quickTo(cta, "x", { duration: 0.55, ease: "power3" });
    const cy = gsap.quickTo(cta, "y", { duration: 0.55, ease: "power3" });
    let first = true;
    window.addEventListener("pointermove", (e) => {
      if (first) { gsap.set(dot, { x: e.clientX, y: e.clientY }); gsap.set(cta, { x: e.clientX + 10, y: e.clientY + 10 }); first = false; }
      dx(e.clientX); dy(e.clientY); cx(e.clientX + 10); cy(e.clientY + 10);
      body.classList.add("cursor-ready");
    }, { passive: true });
    document.addEventListener("mouseleave", () => body.classList.remove("cursor-ready"));

    const styles = ["main", "light"];
    const show = (trigger) => {
      label.textContent = (trigger.getAttribute("data-cta-label") || "").replace(/<[^>]*>/g, "");
      cta.classList.remove(...styles.map((s) => `cursor-cta--${s}`));
      const style = trigger.getAttribute("data-cta-trigger");
      if (style) cta.classList.add(`cursor-cta--${style}`);
      cta.classList.add("cursor-cta--visible");
    };
    $$("[data-cta-trigger]").forEach((trigger) => {
      trigger.addEventListener("mouseenter", () => show(trigger));
      trigger.addEventListener("mouseleave", (e) => {
        const parent = e.relatedTarget && e.relatedTarget.closest ? e.relatedTarget.closest("[data-cta-trigger]") : null;
        if (parent) show(parent);
        else cta.classList.remove("cursor-cta--visible");
      });
    });
    document.addEventListener("mouseover", (e) => {
      const interactive = e.target.closest("a, button, [role=button], input, textarea, select, label");
      const inCta = e.target.closest("[data-cta-trigger]");
      body.classList.toggle("cursor-link", !!interactive && !inCta);
    });
  }

  /* ------------------------------------------------------------ hero intro */
  function heroIntro() {
    const hero = $("[data-hero]");
    const pageHero = $("[data-page-hero]");
    const target = hero || pageHero;
    if (!target) return;
    const media = $(".hero__media, .page-hero__media", target);
    const inner = media ? $("video, img", media) : null;
    const title = $("[data-text-reveal]", target);
    const fades = $$("[data-hero-fade]", target);
    if (reduce) { if (title) gsap.set(title, { visibility: "visible" }); gsap.set(fades, { autoAlpha: 1 }); return; }
    const tl = gsap.timeline({ delay: 0.3 });
    if (media) tl.fromTo(media, { clipPath: "inset(7% 5% 7% 5% round 5px)" }, { clipPath: "inset(0% 0% 0% 0% round 5px)", duration: 1.8, ease: "power3.inOut", clearProps: "clipPath" });
    if (inner) tl.fromTo(inner, { scale: 1.22 }, { scale: 1, duration: 2.6, ease: "power3.out" }, "<");
    tl.fromTo(".header__logo, .header__nav, .hamburger", { autoAlpha: 0, y: -16 }, { autoAlpha: 1, y: 0, duration: 1.1, ease: "power3.out", stagger: 0.08, clearProps: "opacity,visibility,transform" }, "<0.5");
    if (title) tl.textReveal(title, {}, "<0.1");
    if (fades.length) tl.fromTo(fades, { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 1.3, ease: "power3.out", stagger: 0.12 }, "<0.45");

    // scroll-away parallax
    const content = $(".hero__content, .page-hero__content", target);
    if (content) {
      gsap.to(content, { yPercent: -18, opacity: 0.15, ease: "none", scrollTrigger: { trigger: target, start: "top top", end: "bottom top", scrub: true } });
    }
    if (inner) gsap.to(inner, { yPercent: 10, ease: "none", scrollTrigger: { trigger: target, start: "top top", end: "bottom top", scrub: true } });
  }

  /* ------------------------------------------------------------ videos */
  function videos() {
    $$("video[data-autoplay], video[data-hero-video]").forEach((video) => {
      if (reduce) { video.removeAttribute("autoplay"); video.pause(); return; }
      const play = () => { const p = video.play(); if (p && p.catch) p.catch(() => {}); };
      ScrollTrigger.create({ trigger: video, start: "top bottom", end: "bottom top", onEnter: play, onEnterBack: play, onLeave: () => video.pause(), onLeaveBack: () => video.pause() });
    });
  }

  /* ------------------------------------------------------------ scroll reveals */
  function reveals() {
    if (reduce) { gsap.set("[data-fade]", { autoAlpha: 1, y: 0 }); return; }

    $$("[data-fade]").forEach((el) => {
      gsap.to(el, { autoAlpha: 1, y: 0, duration: 1.3, ease: "power3.out", scrollTrigger: { trigger: el, start: "top 90%", once: true } });
    });

    $$("[data-fade-group]").forEach((group) => {
      const kids = group.children;
      gsap.fromTo(kids, { autoAlpha: 0, y: 30 }, { autoAlpha: 1, y: 0, duration: 1.1, ease: "power3.out", stagger: 0.08, scrollTrigger: { trigger: group, start: "top 88%", once: true } });
    });

    $$("[data-reveal-img]").forEach((el) => {
      const img = $("img, video", el);
      gsap.fromTo(el, { clipPath: "inset(14% 10% 0% 10% round 5px)" }, {
        clipPath: "inset(0% 0% 0% 0% round 5px)", ease: "none",
        scrollTrigger: { trigger: el, start: "top bottom", end: "top 45%", scrub: 0.6 },
      });
      if (img) gsap.fromTo(img, { scale: 1.25 }, { scale: 1, ease: "none", scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: 0.6 } });
    });

    $$("[data-parallax]").forEach((el) => {
      const amount = parseFloat(el.getAttribute("data-parallax")) || 10;
      gsap.fromTo(el, { yPercent: -amount }, { yPercent: amount, ease: "none", scrollTrigger: { trigger: el.parentElement, start: "top bottom", end: "bottom top", scrub: true } });
    });

    $$(".badge").forEach((badge, i) => {
      const svg = $("svg", badge);
      gsap.fromTo(badge, { autoAlpha: 0, y: 40, rotate: i % 2 ? 6 : -6 }, { autoAlpha: 1, y: 0, rotate: 0, duration: 1.4, ease: "power3.out", delay: i * 0.12, scrollTrigger: { trigger: badge, start: "top 90%", once: true } });
      if (svg) gsap.fromTo(svg, { rotate: i % 2 ? 8 : -8 }, { rotate: i % 2 ? -8 : 8, ease: "none", scrollTrigger: { trigger: badge, start: "top bottom", end: "bottom top", scrub: 1 } });
    });

    $$("[data-cards-wrapper]").forEach((w) => {
      gsap.fromTo(w, { autoAlpha: 0, y: 80 }, { autoAlpha: 1, y: 0, duration: 1.6, ease: "sine.out", scrollTrigger: { trigger: w, start: "top 85%", once: true } });
    });

    $$(".service__next").forEach((el) => {
      gsap.fromTo(el, { scale: 0.65 }, { scale: 1, ease: "none", scrollTrigger: { trigger: el, scrub: 1, start: "top bottom-=15%", end: "bottom center+=20%" } });
    });

    $$("[data-line]").forEach((el) => {
      gsap.fromTo(el, { scaleX: 0 }, { scaleX: 1, transformOrigin: "left", duration: 1.6, ease: "power3.inOut", scrollTrigger: { trigger: el, start: "top 92%", once: true } });
    });

    $$("[data-count]").forEach((el) => {
      const end = parseFloat(el.getAttribute("data-count"));
      // years (1981, 2017 …) stay static – counting through wrong years would be misleading
      if (end >= 1000) { el.textContent = String(end); return; }
      const obj = { v: 0 };
      el.textContent = "0";
      gsap.to(obj, { v: end, duration: 2, ease: "power2.out", scrollTrigger: { trigger: el, start: "top 90%", once: true }, onUpdate: () => { el.textContent = Math.round(obj.v); } });
    });
  }

  /* ------------------------------------------------------------ image reveal (service top style) */
  function imageRevealIntro() {
    const reveals = $$("[data-image-reveal]");
    if (!reveals.length) return;
    if (reduce) { reveals.forEach((r) => r.style.setProperty("--y", 0)); return; }
    reveals.forEach((wrap, i) => {
      const inner = $(".images, img", wrap);
      const tl = gsap.timeline({ scrollTrigger: { trigger: wrap, start: "top 85%", once: true } });
      tl.to(wrap, { "--y": 0, duration: 1.6, ease: "power3.inOut", delay: i * 0.05 });
      if (inner) tl.fromTo(inner, { yPercent: -45 }, { yPercent: 0, duration: 1.6, ease: "power3.inOut" }, "<");
    });
  }

  /* ------------------------------------------------------------ carousels */
  function carousels() {
    $$("[data-carousel]").forEach((root) => {
      const track = $("[data-track]", root);
      const prev = $("[data-prev]", root);
      const next = $("[data-next]", root);
      if (!track) return;
      const step = () => {
        const card = track.children[0];
        if (!card) return track.clientWidth * 0.8;
        const gap = parseFloat(getComputedStyle(track).columnGap || getComputedStyle(track).gap) || 25;
        return card.getBoundingClientRect().width + gap;
      };
      const update = () => {
        const max = track.scrollWidth - track.clientWidth - 2;
        if (prev) prev.disabled = track.scrollLeft <= 2;
        if (next) next.disabled = track.scrollLeft >= max;
      };
      if (prev) prev.addEventListener("click", () => track.scrollBy({ left: -step(), behavior: "smooth" }));
      if (next) next.addEventListener("click", () => track.scrollBy({ left: step(), behavior: "smooth" }));
      track.addEventListener("scroll", update, { passive: true });
      window.addEventListener("resize", update);
      update();

      // drag to scroll (mouse)
      let down = false, startX = 0, startLeft = 0, moved = 0;
      track.addEventListener("pointerdown", (e) => {
        if (e.pointerType !== "mouse") return;
        down = true; moved = 0; startX = e.clientX; startLeft = track.scrollLeft;
      });
      window.addEventListener("pointermove", (e) => {
        if (!down) return;
        const d = e.clientX - startX;
        moved = Math.max(moved, Math.abs(d));
        if (moved > 6) { track.classList.add("is-dragging"); track.scrollLeft = startLeft - d; }
      });
      window.addEventListener("pointerup", () => {
        if (!down) return;
        down = false;
        setTimeout(() => track.classList.remove("is-dragging"), 30);
      });
      track.addEventListener("click", (e) => { if (moved > 6) { e.preventDefault(); e.stopPropagation(); } }, true);
    });
  }

  /* ------------------------------------------------------------ promise slider */
  function promiseSlider() {
    $$("[data-promise]").forEach((root) => {
      const slides = $$(".promise__slide", root);
      const dots = $$(".promise__dot", root);
      const bar = $(".promise__progress i", root);
      const count = $(".promise__count", root);
      if (slides.length < 2) return;
      let index = 0;
      let tween = null;
      const go = (i) => {
        index = (i + slides.length) % slides.length;
        if (count) count.textContent = `${String(index + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}`;
        slides.forEach((s, k) => s.classList.toggle("is-active", k === index));
        dots.forEach((d, k) => { d.classList.toggle("is-active", k === index); d.setAttribute("aria-current", k === index ? "true" : "false"); });
        if (tween) tween.kill();
        if (bar && !reduce) tween = gsap.fromTo(bar, { scaleX: 0 }, { scaleX: 1, duration: 6, ease: "none", onComplete: () => go(index + 1) });
      };
      dots.forEach((d, k) => d.addEventListener("click", () => go(k)));
      $$("[data-promise-prev]", root).forEach((b) => b.addEventListener("click", () => go(index - 1)));
      $$("[data-promise-next]", root).forEach((b) => b.addEventListener("click", () => go(index + 1)));
      const area = $(".promise__slides", root);
      if (area) {
        let sx = null;
        area.addEventListener("pointerdown", (e) => { sx = e.clientX; });
        area.addEventListener("pointerup", (e) => {
          if (sx === null) return;
          const d = e.clientX - sx;
          if (Math.abs(d) > 40) go(index + (d < 0 ? 1 : -1));
          sx = null;
        });
        area.addEventListener("pointercancel", () => { sx = null; });
      }
      ScrollTrigger.create({ trigger: root, start: "top 80%", once: true, onEnter: () => go(0) });
    });
  }

  /* ------------------------------------------------------------ accordions */
  function accordions() {
    $$(".feature").forEach((f) => {
      const btn = $(".feature__heading", f);
      if (!btn) return;
      btn.addEventListener("click", () => {
        const isOpen = f.classList.toggle("is-open");
        btn.setAttribute("aria-expanded", String(isOpen));
        setTimeout(() => ScrollTrigger.refresh(), 380);
      });
    });
  }

  /* ------------------------------------------------------------ wide gallery */
  function wideGalleries() {
    $$("[data-wide-gallery]").forEach((root) => {
      const track = $(".wide-gallery__track", root);
      const slides = $$(".wide-gallery__slide", root);
      const count = $(".wide-gallery__count", root);
      if (!track || slides.length < 2) return;
      let index = 0;
      const go = (i) => {
        index = (i + slides.length) % slides.length;
        const x = -slides[index].offsetLeft;
        gsap.to(track, { x, duration: reduce ? 0 : 1.1, ease: "power3.inOut" });
        if (count) count.textContent = `${String(index + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}`;
      };
      $$("[data-gal-prev]", root).forEach((b) => b.addEventListener("click", () => go(index - 1)));
      $$("[data-gal-next]", root).forEach((b) => b.addEventListener("click", () => go(index + 1)));
      window.addEventListener("resize", () => gsap.set(track, { x: -slides[index].offsetLeft }));
      let sx = null;
      root.addEventListener("touchstart", (e) => { sx = e.touches[0].clientX; }, { passive: true });
      root.addEventListener("touchend", (e) => { if (sx === null) return; const d = e.changedTouches[0].clientX - sx; if (Math.abs(d) > 40) go(index + (d < 0 ? 1 : -1)); sx = null; });
    });
  }

  /* ------------------------------------------------------------ anchor links */
  function anchors() {
    $$("a[href^='#']").forEach((a) => {
      a.addEventListener("click", (e) => {
        const id = a.getAttribute("href");
        if (id.length < 2) return;
        const target = $(id);
        if (!target) return;
        e.preventDefault();
        scrollTo(target);
      });
    });
  }

  /* ------------------------------------------------------------ init */
  function init() {
    pageTransition();
    headerState();
    megaMenus();
    mobileMenu();
    cursor();
    videos();
    accordions();
    carousels();
    promiseSlider();
    wideGalleries();
    anchors();
    const start = () => {
      heroIntro();
      scrubReveal();
      reveals();
      imageRevealIntro();
      document.dispatchEvent(new CustomEvent("site:ready", { detail: { lenis, gsap, ScrollTrigger } }));
      ScrollTrigger.refresh();
    };
    if (document.fonts && document.fonts.ready) {
      Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 1200))]).then(start);
    } else start();
    window.addEventListener("load", () => ScrollTrigger.refresh());
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
