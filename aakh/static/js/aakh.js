/* AAKH global scripts.
   Everything here is progressive enhancement: the page is fully usable
   without JavaScript (carousel degrades to a list, the accessibility
   panel simply stays hidden). */
(function () {
  "use strict";

  /* =========================================================
     Accessibility options panel
     Preferences are stored in localStorage and mirrored as
     data-a11y-* attributes on <html>; tokens.css reacts to them.
     An inline script in base.html re-applies them before first
     paint so there is no flash of unstyled preferences.
     ========================================================= */
  var PREFS_KEY = "aakh-a11y";
  var PREF_ATTRS = { textsize: "data-a11y-textsize", spacing: "data-a11y-spacing", motion: "data-a11y-motion" };

  function loadPrefs() {
    try {
      return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function savePrefs(prefs) {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    } catch (e) {
      /* Private browsing: preference still applies for this page view. */
    }
  }

  function applyPrefs(prefs) {
    Object.keys(PREF_ATTRS).forEach(function (key) {
      if (prefs[key]) {
        document.documentElement.setAttribute(PREF_ATTRS[key], prefs[key]);
      } else {
        document.documentElement.removeAttribute(PREF_ATTRS[key]);
      }
    });
  }

  function initA11yOptions() {
    var root = document.querySelector("[data-a11y-options]");
    if (!root) return;
    var button = root.querySelector("[data-a11y-toggle]");
    var panel = root.querySelector("[data-a11y-panel]");
    var prefs = loadPrefs();

    /* Reflect stored preferences in the controls. */
    root.querySelectorAll("input[name='textsize']").forEach(function (radio) {
      radio.checked = radio.value === (prefs.textsize || "");
    });
    var spacing = root.querySelector("input[name='spacing']");
    if (spacing) spacing.checked = prefs.spacing === "on";
    var motion = root.querySelector("input[name='motion']");
    if (motion) motion.checked = prefs.motion === "reduce";

    function setOpen(open) {
      button.setAttribute("aria-expanded", String(open));
      panel.hidden = !open;
    }
    setOpen(false);

    button.addEventListener("click", function () {
      setOpen(button.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !panel.hidden) {
        setOpen(false);
        button.focus();
      }
    });
    document.addEventListener("click", function (event) {
      if (!panel.hidden && !root.contains(event.target)) setOpen(false);
    });

    root.addEventListener("change", function (event) {
      var input = event.target;
      if (input.name === "textsize") prefs.textsize = input.value || undefined;
      if (input.name === "spacing") prefs.spacing = input.checked ? "on" : undefined;
      if (input.name === "motion") prefs.motion = input.checked ? "reduce" : undefined;
      applyPrefs(prefs);
      savePrefs(prefs);
    });
  }

  /* =========================================================
     News carousel
     Manual controls only - no autoplay (WCAG 2.2.2, COGA).
     Without JS, all slides render as a plain stacked list.
     ========================================================= */
  function initCarousel(root) {
    var slides = Array.prototype.slice.call(root.querySelectorAll("[data-carousel-slide]"));
    var prev = root.querySelector("[data-carousel-prev]");
    var next = root.querySelector("[data-carousel-next]");
    var status = root.querySelector("[data-carousel-status]");
    var controls = root.querySelector("[data-carousel-controls]");
    if (slides.length < 2) return;  /* single item: leave controls hidden */
    if (controls) controls.hidden = false;
    var index = 0;

    function render() {
      slides.forEach(function (slide, i) {
        slide.hidden = i !== index;
      });
      prev.disabled = index === 0;
      next.disabled = index === slides.length - 1;
      status.textContent = "Slide " + (index + 1) + " of " + slides.length;
    }

    prev.addEventListener("click", function () {
      if (index > 0) index -= 1;
      render();
      if (prev.disabled) next.focus();
    });
    next.addEventListener("click", function () {
      if (index < slides.length - 1) index += 1;
      render();
      if (next.disabled) prev.focus();
    });
    render();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initA11yOptions();
    document.querySelectorAll("[data-carousel]").forEach(initCarousel);
  });
})();
