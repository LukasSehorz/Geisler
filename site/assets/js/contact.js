/* ==========================================================================
   Kontakt – inline validation (German), mailto composition, success state.
   There is no backend: a valid submit opens the visitor's mail client with a
   prepared message. See the HTML comment in contact.html for connecting a
   real form endpoint.
   ========================================================================== */
(function () {
  "use strict";

  var form = document.querySelector("[data-contact-form]");
  if (!form) return;

  var success = document.querySelector("[data-contact-success]");
  var statusEl = form.querySelector("[data-form-status]");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var EMAIL = form.getAttribute("data-email") || "";

  form.setAttribute("novalidate", "");

  var byId = function (id) { return document.getElementById(id); };
  var controls = {
    name: byId("cf-name"),
    phone: byId("cf-phone"),
    email: byId("cf-email"),
    place: byId("cf-place"),
    topic: byId("cf-topic"),
    message: byId("cf-message"),
    privacy: byId("cf-privacy"),
  };

  var rules = {
    name: function (v) {
      if (!v) return "Bitte geben Sie Ihren Vor- und Nachnamen an.";
      if (v.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ]/g, "").length < 2) return "Bitte geben Sie Ihren vollständigen Namen an.";
      return "";
    },
    phone: function (v) {
      if (!v) return "Bitte geben Sie eine Telefonnummer für Rückfragen an.";
      var digits = v.replace(/\D/g, "").length;
      if (!/^[+0-9\s()\/.\-]+$/.test(v) || digits < 6 || digits > 17) return "Bitte geben Sie eine gültige Telefonnummer an, z. B. 09374 / 2124.";
      return "";
    },
    email: function (v) {
      if (!v) return "Bitte geben Sie Ihre E-Mail-Adresse an.";
      if (!/^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[A-Za-z]{2,}$/.test(v)) return "Bitte geben Sie eine gültige E-Mail-Adresse an, z. B. name@beispiel.de.";
      return "";
    },
    message: function (v) {
      if (!v) return "Bitte schildern Sie kurz Ihr Anliegen.";
      if (v.length < 10) return "Bitte beschreiben Sie Ihr Anliegen in ein paar Worten mehr.";
      return "";
    },
    privacy: function (v) {
      return v ? "" : "Bitte bestätigen Sie, dass Sie die Datenschutzerklärung gelesen haben.";
    },
  };
  var order = ["name", "phone", "email", "message", "privacy"];
  var touched = {};

  var wrapOf = function (el) { return el.closest(".field, .checkbox"); };
  var valueOf = function (el) { return el.type === "checkbox" ? el.checked : (el.value || "").trim(); };

  function setError(el, msg) {
    var wrap = wrapOf(el);
    var err = byId(el.id + "-error");
    if (wrap) wrap.classList.toggle("is-invalid", !!msg);
    if (msg) el.setAttribute("aria-invalid", "true");
    else el.removeAttribute("aria-invalid");
    if (err) err.textContent = msg || "";
  }

  function validate(key) {
    var el = controls[key];
    if (!el || !rules[key]) return "";
    var msg = rules[key](valueOf(el));
    setError(el, msg);
    if (!msg && statusEl && statusEl.textContent && !form.querySelector(".is-invalid")) statusEl.textContent = "";
    return msg;
  }

  order.forEach(function (key) {
    var el = controls[key];
    if (!el) return;
    var isInvalid = function () { var w = wrapOf(el); return w && w.classList.contains("is-invalid"); };
    el.addEventListener("input", function () {
      touched[key] = true;
      if (isInvalid()) validate(key);
    });
    el.addEventListener("blur", function () {
      if (touched[key]) validate(key);
    });
    el.addEventListener("change", function () {
      touched[key] = true;
      if (el.type === "checkbox" || isInvalid()) validate(key);
    });
  });

  /* ---------------------------------------------------------------- select state + ?anliegen= preselect */
  var topicWrap = controls.topic ? wrapOf(controls.topic) : null;
  var syncTopic = function () {
    if (topicWrap) topicWrap.classList.toggle("is-filled", !!controls.topic.value);
  };
  if (controls.topic) {
    controls.topic.addEventListener("change", syncTopic);
    try {
      var wanted = new URLSearchParams(window.location.search).get("anliegen");
      if (wanted) {
        var opts = controls.topic.querySelectorAll("option[data-slug]");
        for (var i = 0; i < opts.length; i++) {
          if (opts[i].getAttribute("data-slug") === wanted) { opts[i].selected = true; break; }
        }
      }
    } catch (e) { /* ignore */ }
    syncTopic();
    window.addEventListener("pageshow", syncTopic);
  }

  /* ---------------------------------------------------------------- helpers */
  function headerHeight() {
    var h = document.querySelector(".header");
    return h ? h.offsetHeight : 80;
  }

  function bringIntoView(target, force) {
    var r = target.getBoundingClientRect();
    var top = headerHeight() + 20;
    var visible = r.top >= top && r.bottom <= window.innerHeight - 20;
    if (visible && !force) return;
    var lenis = window.__lenis;
    if (lenis) lenis.scrollTo(target, { offset: -(headerHeight() + 60), duration: reduce ? 0 : 0.9 });
    else target.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }

  function focusControl(el) {
    bringIntoView(wrapOf(el) || el);
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
  }

  function refreshTriggers() {
    if (window.ScrollTrigger) window.setTimeout(function () { window.ScrollTrigger.refresh(); }, 60);
  }

  /* ---------------------------------------------------------------- mail composition */
  function compose() {
    var d = {
      name: valueOf(controls.name),
      phone: valueOf(controls.phone),
      email: valueOf(controls.email),
      place: controls.place ? valueOf(controls.place) : "",
      topic: controls.topic ? controls.topic.value : "",
      message: valueOf(controls.message).replace(/\r?\n/g, "\r\n"),
    };
    var subject = "Anfrage über die Website" + (d.topic ? " – " + d.topic : "");
    var greeted = /^(guten\s+(tag|morgen|abend)|hallo|sehr\s+geehrte|liebe[rs]?\s|moin|servus|grüß|gruess)/i.test(d.message);
    var lines = (greeted ? [] : ["Guten Tag,", ""]).concat([
      d.message,
      "",
      "",
      "Meine Kontaktdaten",
      "Name: " + d.name,
      "Telefon: " + d.phone,
      "E-Mail: " + d.email,
    ]);
    if (d.place) lines.push("PLZ / Ort: " + d.place);
    if (d.topic) lines.push("Anliegen: " + d.topic);
    lines.push(
      "",
      "Ich habe die Datenschutzerklärung gelesen und bin mit der Verarbeitung meiner Angaben zur Beantwortung meiner Anfrage einverstanden.",
      "",
      "Mit freundlichen Grüßen",
      d.name
    );
    var body = lines.join("\r\n");
    return {
      data: d,
      subject: subject,
      body: body,
      href: "mailto:" + EMAIL + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body),
    };
  }

  /* ---------------------------------------------------------------- success panel */
  var copyText = "";

  function showSuccess(mail) {
    if (!success) return;
    var nameEl = success.querySelector("[data-success-name]");
    if (nameEl) nameEl.textContent = mail.data.name.split(/\s+/)[0];
    var again = success.querySelector("[data-success-mailto]");
    if (again) again.setAttribute("href", mail.href);
    copyText = "An: " + EMAIL + "\nBetreff: " + mail.subject + "\n\n" + mail.body.replace(/\r\n/g, "\n");

    var gsap = window.gsap;
    var swap = function () {
      form.hidden = true;
      success.hidden = false;
      bringIntoView(success, success.getBoundingClientRect().top < headerHeight());
      try { success.focus({ preventScroll: true }); } catch (e) { success.focus(); }
      refreshTriggers();
    };

    if (gsap && !reduce) {
      var anims = success.querySelectorAll("[data-success-anim]");
      gsap.to(form, {
        autoAlpha: 0, y: -14, duration: 0.45, ease: "power2.in",
        onComplete: function () {
          // opacity only (no visibility:hidden) so the panel can keep focus while fading in
          gsap.set(success, { opacity: 0, y: 30 });
          gsap.set(anims, { opacity: 0, y: 18 });
          swap();
          gsap.to(success, { opacity: 1, y: 0, duration: 1.1, ease: "power3.out" });
          gsap.to(anims, { opacity: 1, y: 0, duration: 1, ease: "power3.out", stagger: 0.08, delay: 0.15 });
          var marks = success.querySelectorAll(".contact-success__check circle, .contact-success__check path");
          gsap.fromTo(marks, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.2, ease: "power2.inOut", stagger: 0.35, delay: 0.2 });
        },
      });
    } else {
      swap();
    }
  }

  function resetForm() {
    form.reset();
    touched = {};
    order.forEach(function (key) { if (controls[key]) setError(controls[key], ""); });
    if (statusEl) statusEl.textContent = "";
    syncTopic();
    success.hidden = true;
    form.hidden = false;
    var gsap = window.gsap;
    if (gsap) gsap.set(form, { visibility: "visible", opacity: reduce ? 1 : 0, y: reduce ? 0 : 24 });
    refreshTriggers();
    focusControl(controls.name);
    if (gsap && !reduce) gsap.to(form, { opacity: 1, y: 0, duration: 0.9, ease: "power3.out" });
  }

  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "0";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  if (success) {
    var copyBtn = success.querySelector("[data-success-copy]");
    var resetBtn = success.querySelector("[data-success-reset]");
    if (copyBtn) {
      var label = copyBtn.querySelector("span") || copyBtn;
      var original = label.textContent;
      var timer = null;
      var done = function (ok) {
        label.textContent = ok ? "Anfrage kopiert" : "Kopieren nicht möglich";
        window.clearTimeout(timer);
        timer = window.setTimeout(function () { label.textContent = original; }, 2600);
      };
      copyBtn.addEventListener("click", function () {
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(copyText).then(function () { done(true); }, function () { done(legacyCopy(copyText)); });
        } else {
          done(legacyCopy(copyText));
        }
      });
    }
    if (resetBtn) resetBtn.addEventListener("click", resetForm);
  }

  /* ---------------------------------------------------------------- submit */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var invalid = [];
    order.forEach(function (key) {
      touched[key] = true;
      if (validate(key)) invalid.push(controls[key]);
    });
    if (invalid.length) {
      if (statusEl) {
        statusEl.textContent = invalid.length === 1
          ? "Bitte prüfen Sie das markierte Feld."
          : "Bitte prüfen Sie die " + invalid.length + " markierten Felder.";
      }
      focusControl(invalid[0]);
      return;
    }
    if (statusEl) statusEl.textContent = "";
    var mail = compose();
    try { window.location.href = mail.href; } catch (err) { /* no mail handler */ }
    showSuccess(mail);
  });
})();
