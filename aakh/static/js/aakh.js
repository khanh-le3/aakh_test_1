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

    /* The button is hidden in the template so that a no-JS page never shows a
       control that does nothing when clicked. JS is running, so reveal it. */
    button.hidden = false;

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
     Back to top
     The native fragment link also works without JavaScript.
     Enhancement hides it while the page header is still visible.
     ========================================================= */
  function initBackToTop() {
    var link = document.querySelector("[data-back-to-top]");
    var top = document.querySelector(".header") || document.getElementById("page-top");
    if (!link || !top || !("IntersectionObserver" in window)) return;
    var atTop = top.getBoundingClientRect().bottom > 0;

    function updateVisibility() {
      // Never hide a control while it holds keyboard focus.
      link.hidden = atTop && document.activeElement !== link;
    }
    updateVisibility();
    new IntersectionObserver(function (entries) {
      atTop = entries[0].isIntersecting;
      updateVisibility();
    }).observe(top);
    link.addEventListener("blur", updateVisibility);

    document.addEventListener("focusin", function (event) {
      if (link.hidden || link.contains(event.target)) return;
      // A whole-card link can be taller than a short viewport. Keep its
      // heading in view rather than centring the entire card off-screen.
      var target = event.target.querySelector("h1, h2, h3, h4, h5, h6") || event.target;
      var focused = target.getBoundingClientRect();
      var control = link.getBoundingClientRect();
      if (focused.bottom > control.top && focused.top < control.bottom &&
          focused.right > control.left && focused.left < control.right) {
        target.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
      }
    });
  }

  /* =========================================================
     Sticky navigation clearance
     Measure the wrapping navigation before enabling stickiness.
     CSS uses this height only at its sticky-navigation breakpoints.
     ========================================================= */
  function initStickyNavigation(onChange) {
    var navigation = document.querySelector(".site-nav");
    if (!navigation) return;
    var html = document.documentElement;
    var pending = false;
    var height = 0;

    function measure() {
      pending = false;
      var nextHeight = Math.ceil(navigation.getBoundingClientRect().height);
      if (nextHeight > 0 && nextHeight !== height) {
        height = nextHeight;
        html.style.setProperty("--site-nav-height", height + "px");
        html.setAttribute("data-sticky-nav-ready", "");
      }
      if (onChange) onChange();
    }

    function schedule() {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(measure);
    }

    measure();
    window.addEventListener("resize", schedule);
    window.addEventListener("load", schedule);
    if ("ResizeObserver" in window) {
      new ResizeObserver(schedule).observe(navigation);
    }
    // Preferences can change line wrapping without a window resize.
    if ("MutationObserver" in window) {
      new MutationObserver(schedule).observe(html, {
        attributes: true,
        attributeFilter: Object.keys(PREF_ATTRS).map(function (key) { return PREF_ATTRS[key]; })
      });
    }
    if (document.fonts) {
      document.fonts.ready.then(schedule);
      document.fonts.addEventListener("loadingdone", schedule);
    }
  }

  /* =========================================================
     Resource contents: current reading position
     Native fragment links retain their keyboard/history behaviour.
     Scrolling only updates the current state, never document focus.
     ========================================================= */
  function initResourceContents() {
    var toc = document.querySelector(".resource-toc");
    var sidebar = document.querySelector(".resource-sidebar");
    var content = document.querySelector(".resource-content");
    if (!sidebar || !content) return null;
    var list = toc ? toc.querySelector(".resource-toc__list") : null;
    var navigation = document.querySelector(".site-nav");
    var entries = [];
    sidebar.querySelectorAll(".resource-toc__link[href^='#']").forEach(function (link) {
      var id;
      try {
        id = decodeURIComponent(link.getAttribute("href").slice(1));
      } catch (e) {
        return;
      }
      var heading = document.getElementById(id);
      if (heading && content.contains(heading) && heading.matches("h2, h3")) {
        entries.push({ link: link, heading: heading });
      }
    });
    var current = -1;
    var pending = false;
    var sidebarFitKey = "";

    function sizeContentsToArticle() {
      var style = window.getComputedStyle(sidebar);
      var download = sidebar.querySelector(".resource-sidebar__download");
      var minimum = download ? download.getBoundingClientRect().height : 0;
      if (list) {
        var title = toc.querySelector(".resource-toc__title");
        var tocStyle = window.getComputedStyle(toc);
        var titleStyle = window.getComputedStyle(title);
        var listStyle = window.getComputedStyle(list);
        var tallestLink = Math.max.apply(null, entries.map(function (entry) {
          return entry.link.getBoundingClientRect().height;
        }));
        minimum += title.getBoundingClientRect().height + (parseFloat(titleStyle.marginBottom) || 0) +
          (parseFloat(tocStyle.paddingTop) || 0) + (parseFloat(tocStyle.paddingBottom) || 0) +
          (parseFloat(tocStyle.borderTopWidth) || 0) + (parseFloat(tocStyle.borderBottomWidth) || 0) +
          (download ? parseFloat(style.rowGap) || 0 : 0) +
          (parseFloat(listStyle.paddingTop) || 0) + (parseFloat(listStyle.paddingBottom) || 0) +
          tallestLink;
      }
      // Every contents link, the title and the download must fit. Recheck
      // when their size or the viewport changes, keeping normal scrolling
      // stable while a large-text sidebar cannot fit in the viewport.
      var fitKey = [window.innerWidth, window.innerHeight, minimum, style.top].join("/");
      if (fitKey !== sidebarFitKey) {
        sidebarFitKey = fitKey;
        sidebar.removeAttribute("data-sticky-disabled");
        sidebar.style.removeProperty("--resource-toc-available-height");
        style = window.getComputedStyle(sidebar);
        if (style.position === "sticky" && minimum > parseFloat(style.maxHeight)) {
          sidebar.setAttribute("data-sticky-disabled", "");
          return;
        }
      }
      if (style.position !== "sticky") {
        sidebar.style.removeProperty("--resource-toc-available-height");
        return;
      }
      // Shorten the scrollable list near the article's end so its title is
      // not pushed underneath the main menu by the sticky containing block.
      // CSS still caps the entire panel to the available viewport height.
      var available = Math.max(minimum, content.getBoundingClientRect().bottom - parseFloat(style.top));
      var value = Math.floor(available) + "px";
      if (sidebar.style.getPropertyValue("--resource-toc-available-height") !== value) {
        sidebar.style.setProperty("--resource-toc-available-height", value);
      }
    }

    function keepCurrentVisible(link) {
      // Follow the article inside the list only. Never move keyboard focus
      // or interrupt someone who is navigating the contents themselves.
      if (!list || list.scrollHeight <= list.clientHeight || toc.contains(document.activeElement)) return;
      var listRect = list.getBoundingClientRect();
      var linkRect = link.getBoundingClientRect();
      var style = window.getComputedStyle(list);
      var top = listRect.top + list.clientTop + (parseFloat(style.scrollPaddingTop) || 0);
      var bottom = listRect.top + list.clientTop + list.clientHeight - (parseFloat(style.scrollPaddingBottom) || 0);
      if (linkRect.top < top || linkRect.height > bottom - top) {
        list.scrollTop += linkRect.top - top;
      } else if (linkRect.bottom > bottom) {
        list.scrollTop += linkRect.bottom - bottom;
      }
    }

    function update() {
      pending = false;
      var readingLine = 0;
      if (navigation) {
        var position = window.getComputedStyle(navigation).position;
        var navigationRect = navigation.getBoundingClientRect();
        if ((position === "sticky" || position === "fixed") &&
            navigationRect.top <= 1 && navigationRect.bottom > 0) {
          readingLine = navigationRect.bottom;
        }
      }
      // Mark the first H2/H3 whose start is visible below the navigation.
      // The extra gap used for anchor scrolling is not an obstruction.
      // Allow one pixel for fractional layout, but never retain a heading
      // that has scrolled underneath the navigation or outside the viewport.
      var next = -1;
      entries.some(function (entry, index) {
        var rect = entry.heading.getBoundingClientRect();
        if (rect.height > 0 && rect.top >= readingLine - 1 &&
            rect.top < window.innerHeight && rect.bottom > readingLine) {
          next = index;
          return true;
        }
        return false;
      });
      if (next !== current) {
        entries.forEach(function (entry, index) {
          if (index === next) entry.link.setAttribute("aria-current", "location");
          else entry.link.removeAttribute("aria-current");
        });
        current = next;
      }
      sizeContentsToArticle();
      if (current !== -1) keepCurrentVisible(entries[current].link);
    }

    function schedule() {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(update);
    }

    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    window.addEventListener("hashchange", schedule);
    window.addEventListener("pageshow", schedule);
    window.addEventListener("load", schedule);
    sidebar.addEventListener("focusin", schedule);
    sidebar.addEventListener("focusout", schedule);
    if ("ResizeObserver" in window) new ResizeObserver(schedule).observe(content);
    schedule();
    return schedule;
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
    initBackToTop();
    initStickyNavigation(initResourceContents());
    document.querySelectorAll("[data-carousel]").forEach(initCarousel);
  });
})();
