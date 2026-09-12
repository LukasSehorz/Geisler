/* ==========================================================================
   Rechtliches – sections, sticky table of contents with active state,
   title reveal and section fades (Impressum & Datenschutz).
   ========================================================================== */
(function () {
  "use strict";

  var legal = document.querySelector("[data-legal]");
  if (!legal) return;

  var toc = document.querySelector("[data-legal-toc]");
  var list = toc ? toc.querySelector(".legal-toc__list") : null;
  var toggle = toc ? toc.querySelector(".legal-toc__toggle") : null;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var built = false;
  var heads = [];
  var links = [];
  var current = -1;

  var pad = function (n) { return (n < 10 ? "0" : "") + n; };
  var slugify = function (s) {
    return s.toLowerCase()
      .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
      .replace(/§/g, "paragraf")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60);
  };
  var headerOffset = function () {
    var h = document.querySelector(".header");
    return (h ? h.offsetHeight : 80) + 40;
  };

  // document offset that ignores CSS transforms (sections may still be mid fade-in)
  function absTop(el) {
    var y = 0;
    while (el) { y += el.offsetTop; el = el.offsetParent; }
    return y;
  }

  function scrollToTarget(target, immediate) {
    var y = Math.max(0, absTop(target) - headerOffset());
    var lenis = window.__lenis;
    if (lenis) lenis.scrollTo(y, { duration: reduce || immediate ? 0 : 1.2, immediate: !!immediate });
    else window.scrollTo({ top: y, behavior: reduce || immediate ? "auto" : "smooth" });
  }

  function setOpen(open) {
    if (!toc || !toggle) return;
    toc.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    if (window.ScrollTrigger) window.setTimeout(function () { window.ScrollTrigger.refresh(); }, 50);
  }

  function setActive(idx) {
    if (idx === current) return;
    current = idx;
    links.forEach(function (a, k) {
      a.classList.toggle("is-active", k === idx);
      if (k === idx) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }

  function update() {
    if (!heads.length) return;
    var line = window.innerHeight * 0.32;
    var idx = 0;
    for (var i = 0; i < heads.length; i++) {
      if (heads[i].getBoundingClientRect().top <= line) idx = i;
      else break;
    }
    var doc = document.documentElement;
    var lastTop = heads[heads.length - 1].getBoundingClientRect().top;
    if (window.innerHeight + window.pageYOffset >= doc.scrollHeight - 4 && lastTop < window.innerHeight) idx = heads.length - 1;
    setActive(idx);
  }

  // keep legal references together: "§ 18", "Abs. 2", "Art. 6", "lit. f"
  function tieReferences(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      node.nodeValue = node.nodeValue.replace(/(§|Abs\.|Art\.|lit\.|Nr\.) +(?=[0-9A-Za-z])/g, "$1 ");
    }
  }

  function build() {
    if (built) return;
    built = true;
    tieReferences(legal);
    var used = {};
    heads = Array.prototype.slice.call(legal.querySelectorAll("h2"));

    heads.forEach(function (h, i) {
      // collapse ordinary whitespace only – \s would also eat the no-break spaces set above
      var raw = h.textContent.replace(/[ \t\r\n]+/g, " ").replace(/^ +| +$/g, "");
      var match = raw.match(/^(\d+)\.\s*(.+)$/);
      var text = match ? match[2] : raw;
      var num = pad(match ? parseInt(match[1], 10) : i + 1);
      var id = slugify(text) || "abschnitt-" + (i + 1);
      while (used[id]) id += "-" + (i + 1);
      used[id] = true;

      h.id = id;
      h.textContent = "";
      var numEl = document.createElement("span");
      numEl.className = "legal__num";
      numEl.textContent = num;
      if (!match) numEl.setAttribute("aria-hidden", "true");
      var textEl = document.createElement("span");
      textEl.className = "legal__heading";
      textEl.textContent = text;
      h.appendChild(numEl);
      h.appendChild(textEl);

      // wrap the heading and its following content into a section
      var section = document.createElement("section");
      section.className = "legal__section";
      section.setAttribute("aria-labelledby", id);
      legal.insertBefore(section, h);
      var node = h;
      do {
        var next = node.nextSibling;
        section.appendChild(node);
        node = next;
      } while (node && !(node.nodeType === 1 && node.tagName === "H2"));

      if (list) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.className = "legal-toc__link";
        a.href = "#" + id;
        a.innerHTML = '<span class="legal-toc__num" aria-hidden="true"></span><span class="legal-toc__text"></span>';
        a.firstChild.textContent = num;
        a.lastChild.textContent = text;
        a.addEventListener("click", function (e) {
          e.preventDefault();
          // collapse the mobile TOC first so the target position is measured after the layout shift
          if (toc && toc.classList.contains("is-open")) setOpen(false);
          scrollToTarget(h);
          try { window.history.replaceState(null, "", "#" + id); } catch (err) { /* file:// */ }
          setActive(i);
        });
        li.appendChild(a);
        list.appendChild(li);
        links.push(a);
      }
    });

    if (toc && links.length > 1) toc.hidden = false;
    if (toggle) toggle.addEventListener("click", function () { setOpen(!toc.classList.contains("is-open")); });

    var ticking = false;
    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { ticking = false; update(); });
    }, { passive: true });
    window.addEventListener("resize", update);
    var hashTarget = function () {
      if (!window.location.hash) return null;
      var el = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
      return el && el.tagName === "H2" ? el : null;
    };
    window.addEventListener("hashchange", function () {
      var target = hashTarget();
      if (target) scrollToTarget(target);
    });
    // the browser retries its native fragment jump until "load" (ids are assigned by JS),
    // which can land while a section is still offset by its fade-in – re-apply once loaded
    window.addEventListener("load", function () {
      window.setTimeout(function () {
        var target = hashTarget();
        if (target) scrollToTarget(target, true);
      }, 60);
    });
    update();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();

  document.addEventListener("site:ready", function (e) {
    build();
    var gsap = e.detail && e.detail.gsap;
    if (!gsap) return;

    var title = document.querySelector(".legal-page [data-text-reveal]");
    if (title) {
      if (reduce) gsap.set(title, { visibility: "visible" });
      else gsap.delayedCall(0.2, function () { gsap.effects.textReveal(title); });
    }

    // deep link (#abschnitt): scroll before the fade tweens offset the sections
    if (window.location.hash) {
      var target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
      if (target) scrollToTarget(target, true);
    }

    if (!reduce) {
      gsap.utils.toArray(".legal__section").forEach(function (section) {
        gsap.from(section, { autoAlpha: 0, y: 36, duration: 1.2, ease: "power3.out", scrollTrigger: { trigger: section, start: "top 92%", once: true } });
      });
      if (links.length && window.matchMedia("(min-width: 1001px)").matches) {
        gsap.from(links, { autoAlpha: 0, x: -10, duration: 0.8, ease: "power3.out", stagger: 0.035, delay: 0.5 });
      }
    }

    if (e.detail.ScrollTrigger) e.detail.ScrollTrigger.refresh();
    update();
  });
})();
