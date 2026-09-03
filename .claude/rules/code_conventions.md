# C. Code conventions — AAKH website

**Purpose of this document.** It records the code-level conventions this
codebase already follows, so they survive across contributors and sessions.

Every rule here is derived from existing code, not aspiration. If a rule and
the code disagree, that is a bug in one of them — say so rather than silently
following the other.

**Scope test.** A convention earns a place here only if a competent developer
new to this repo could reasonably guess wrong. Generic virtues (modularity,
maintainability, DRY, SOLID) are deliberately absent: they are unfalsifiable,
they are baseline behaviour anyway, and every line here is re-read on every
turn, so filler crowds out the rules that carry weight.

**Status labels.** As in `information_architecture.md`:

| Label | Meaning |
|---|---|
| `DECIDED` | Settled. Do not re-litigate; implement as written. |
| `PROPOSED` | Intended, but not yet confirmed. Flag before building on it. |
| `OPEN` | Unresolved. Ask before assuming an answer. |

---

## C.0. Precedence — `DECIDED`

When two rules conflict, the higher one wins:

1. `accessibility.md` — the required accessibility features. Overrides
   everything below it, including any visual or layout preference.
2. `information_architecture.md` — sitemap, URLs, page models.
3. `code_conventions.md` — this file.
4. `design_system.md` — visual styling.
5. `techstack.md` — platform and hosting constraints.

`references.md` is **not** in this chain. It is the evidence base — W3C notes,
WCAG, Australian Government standards, and the autism/accessibility research
literature. It states no directives. Cite it when justifying a decision or
resolving a question the chain above does not answer.

An accessibility requirement beating a design preference is not a compromise
to be negotiated. It is the order of authority.

---

## C.1. CSS — `DECIDED`

### Naming: BEM, strictly

`block__element--modifier`. All 617 lines of `aakh.css` currently conform with
**zero** deviations. Keep it that way.

```css
.card            .card__title          .card__title--compact
.footer          .footer__ack          .footer__ack--cols
```

### Tokens: two tiers, never skipped

`tokens.css` defines two layers, and the separation is the whole reason a new
colour scheme is a single edit:

```
--aakh-navy-900     PRIMITIVE   raw palette. Set ONLY in tokens.css.
      ↓
--color-brand       SEMANTIC    what the colour is *for*.
      ↓
used by components in aakh.css
```

**A component must never reference an `--aakh-*` primitive directly, and must
never hardcode a raw colour.** Need a colour that has no semantic token? Add
the semantic token — do not reach past the layer. Breaking this contract is
what makes a dark theme cost a hundred edits instead of one block.

### Interactive states stay in one family

Rest, hover, active and focus of one element always come from the **same
semantic family**, and every family that can be the resting colour of an
interactive element carries its own `-hover` partner:

```css
--color-brand: var(--aakh-navy-900);        --color-brand-hover: var(--aakh-navy-950);
--color-interactive: var(--aakh-teal-600);  --color-interactive-hover: var(--aakh-teal-800);
```

Never borrow a hover from another family. That is how the primary nav came to
rest navy and hover teal — a hue jump — while body links darkened in place. If
a family has no partner, add one and measure it.

Where a family is already very dark, colour alone is not enough feedback:
navy-900 → navy-950 is a 1.25:1 step, against 1.97:1 for the teal links. Pair
it with a second cue — the nav uses its underline bar. A state change must
never be signalled by colour alone.

Do not derive hover with `color-mix()`. It is one rule for any hue, and it
yields contrast nobody verified.

### File organisation: atomic design, and the cascade depends on it

`aakh.css` is ordered in five numbered sections. The order is load-bearing,
not cosmetic:

| # | Section | Contains |
|---|---|---|
| 1 | Base | Element defaults, focus style |
| 2 | Utilities | `.container`, `.visually-hidden`, `[hidden]`, `.skip-link` |
| 3 | Atoms | `.icon`, `.btn`, `.link-more`, `.tag`, `.meta`, `.input` |
| 4 | Molecules | `.search-form`, `.a11y-options`, `.card`, `.news-panel`, `.subscribe-form` |
| 5 | Organisms | `.header`, `.site-nav`, `.hero`, `.section`, `.carousel`, `.footer` |

A molecule may legitimately override an atom it contains, so **atoms must come
first or the override silently fails**. Add a new component to its numbered
section — never to the end of the file. Markers look like:

```css
/* --- 4. Molecules: cards -------------------------------------------------- */
```

`tokens.css` has its own three-part order for the same reason: 1. Primitives,
2. Semantic, 3. Preference overrides (`html[data-a11y-*]`).

Both files are currently in strict conformance. Keep them there — this kind of
ordering decays silently and is expensive to restore.

### No build step

Plain CSS, served by Django staticfiles. No framework, no preprocessor, no
bundler, no `package.json`. Do not introduce Tailwind, Sass, or npm without
raising it first — it is a project-level decision, not a file-level one.

### Breakpoints — and why mobile has none

The CSS is **mobile-first**: everything outside a media query *is* the mobile
layout. Complexity is added as the viewport grows. There is no "mobile
breakpoint" to look for — mobile is the default, not a special case.

| Query | Width | What it adds |
|---|---|---|
| `@media (min-width: 48em)` | 768px | Footer becomes multi-column |
| `@media (min-width: 64em)` | 1024px | Hero and news panel become two-column |
| `@media (max-width: 63.99em)` | below 1024px | The one exception: reorders the news image above its text |

Three queries, not two — and the `max-width` one is the single deliberate
departure from mobile-first. Keep such exceptions rare, and always paired with
the `min-width` rule they complement.

**Breakpoints are in `em`, never `px`, and that is an accessibility decision.**
An `em` breakpoint scales with the user's browser font setting, so someone
browsing at a 24px default font reaches the simpler layout sooner — precisely
when they need it. A `px` breakpoint ignores them entirely. This matters more
here than on most sites, because `data-a11y-textsize="xl"` scales the root
font to 130% on top of whatever the user has already set.

**The real floor is 320 CSS pixels, not 768.** WCAG 2.2 SC 1.4.10 Reflow
(Level AA) requires content to be presented "without requiring scrolling in
two dimensions for: Vertical scrolling content at a width equivalent to 320
CSS pixels". Its note adds that 320px is equivalent to a 1280px viewport at
400% zoom — so testing at 320px discharges the zoom case at the same time.

Test every layout at 320px wide: no horizontal scrollbar, no clipped content,
no overlapping text. That is the width that has to work. 768 and 1024 are
merely where the layout is allowed to get richer.

### Colour contrast is a hard gate

Every foreground/background pair ships only after being checked against
WCAG 2.2 AA (4.5:1 body text, 3:1 large text and UI boundaries).

Measured against the ivory background `#F7F5F0`:

| Pair | Ratio | Verdict |
|---|---|---|
| navy `#032059` on ivory | 14.23:1 | Safe anywhere |
| teal `#0B7A66` on ivory | 4.83:1 | Passes AA body — little headroom, do not lighten |
| **gold `#C9A227` on ivory** | **2.22:1** | **Fails at every size** |
| navy on gold | 6.41:1 | Safe — this is how gold is used |

**Wattle gold is a background and focus-ring colour, never a text or icon
colour on a light ground.**

Windows High Contrast Mode (`forced-colors`) discards custom properties
entirely, so components carry transparent-border fallbacks to keep their
boundaries visible. Preserve them.

---

## C.2. JavaScript — `DECIDED`

Vanilla ES, IIFE-scoped, no framework and no bundler.

### Why — and what WCAG actually says

**No WCAG 2.2 success criterion requires a page to work with JavaScript
disabled.** Nor does any of its five conformance requirements. State this
accurately: the rule is widely misquoted as a WCAG obligation, and it is not.

The requirement did exist, once. **WCAG 1.0 (1999), Checkpoint 6.3,
Priority 1:** *"Ensure that pages are usable when scripts, applets, or other
programmatic objects are turned off or not supported."* WCAG 1.0 was
superseded in May 2021, and that checkpoint has no successor in WCAG 2.x,
which is deliberately technology-agnostic.

What WCAG 2.2 *does* govern is how JS-driven UI must behave once it exists:

| Success criterion | Level | Bites us where |
|---|---|---|
| 4.1.2 Name, Role, Value | A | Custom controls must expose name, role and state — carousel buttons, the panel's `aria-expanded` |
| 2.1.1 Keyboard | A | Every JS control operable by keyboard |
| 2.1.2 No Keyboard Trap | A | Focus must not be trapped inside the a11y panel |
| 3.2.1 On Focus / 3.2.2 On Input | A | Focusing or changing a control must not change context unexpectedly — a filter `<select>` must never auto-submit |
| 2.2.2 Pause, Stop, Hide | A | Why the carousel is manual-only, with no autoplay |

Conformance Requirement 5.2.4 adds that only *accessibility-supported* ways of
using a technology may be relied upon to satisfy a criterion; 5.2.5
Non-Interference requires 1.4.2, 2.1.2, 2.2.2 and 2.3.1 to hold for all
content, whether or not it is relied upon for conformance.

So progressive enhancement here is a **resilience and reach decision, not a
conformance obligation.** It stands on its own evidence instead:

> GDS measured **1.1%** of visitors to GOV.UK not receiving JavaScript, across
> 500,000+ visits. Only **0.2%** had disabled it deliberately. The other
> **0.9%** were failures — corporate proxies stripping scripts, blocked CDNs,
> browser extensions, mobile network errors, and users who left before the
> script finished.

That 0.9% cannot be detected or served any other way. For a publicly funded
health-information service, silently failing roughly 1 visitor in 93 is not a
trade we get to make. The autistic and cognitively disabled audience this site
exists for is also disproportionately likely to be on older devices, locked-down
institutional networks, or assistive setups where scripts break.


### Progressive enhancement, defined precisely

> **If JS never loads, the user loses convenience — never content, and never
> a capability.**

"Works without JS" does not mean *identical* without JS. It means nothing
becomes unreachable. Three tiers:

**1. Fetch, filter, search, submit, paginate → server-side. Always.**

A `<form method="get">` and a queryset. The result is bookmarkable,
shareable, in browser history, and indexable, and it survives a flaky mobile
connection.

This explicitly includes the asset-type filter in `information_architecture.md`
B.3.3. Filter with `?type=snapshot` against the queryset — **not** by toggling
`hidden` on cards client-side, which silently destroys the ability to link
someone to a filtered view.

**2. Presentation of content already in the DOM → JS may enhance it.**

Ship the complete content in HTML; let JS reshape it. The news carousel is the
reference implementation: every slide is server-rendered, and JS collapses the
stack into a paged view. With JS off it degrades to a plain list — nothing is
lost. The tell is that JS *rearranges* content it did not *deliver*.

For simple disclosure, prefer `<details>`/`<summary>` — no JS at all.

**3. Persisted client-side preference → JS-only is acceptable.**

The server cannot read `localStorage`, so the accessibility options panel has
no server-side equivalent. This tier is legitimate, under one condition:

> **The no-JS default must already meet WCAG 2.2 AA on its own.**

The panel improves on an accessible baseline; it is never the mechanism by
which compliance is achieved. Concretely: browser zoom already satisfies
SC 1.4.4, and `prefers-reduced-motion` is honoured in CSS in `tokens.css`
independently of the panel. Keep it that way — never move an OS-level
accessibility signal into JS.

### Never render a dead control

A control that only functions with JS must be `hidden` in the template and
revealed by JS on init:

```html
<div class="carousel__controls" data-carousel-controls hidden>
```
```js
if (controls) controls.hidden = false;
```

A visible button that does nothing when clicked is worse than an absent one,
and unpredictable response is a documented barrier for cognitively disabled
and autistic users (COGA).

### Hooks

JS selects elements by `data-*` attribute, never by class name. Classes are
for styling; data attributes are the behaviour contract. This means renaming a
CSS class cannot break behaviour.

---

## C.3. Python / Wagtail — `DECIDED`

### Docstrings explain *why*, and cite the rule they implement

Every model and module carries a docstring, and where it implements a decision
it names the section:

```python
class HomePage(Page):
    """The site home page: hero, featured resources, news and updates.

    See .claude/rules/information_architecture.md section B.3.1.
    """
```

This is the mechanism that keeps the rules and the code from drifting apart.
Maintain it.

### Page models

- Set `parent_page_types` / `subpage_types` on **every** page model, and
  `max_count` where the IA fixes a count (IA B.4.5). These are guardrails an
  editor feels in the admin, not rules they must remember.
- Cross-field validation lives in `clean()`, and its error messages are
  written for a content editor, not a developer:

  ```python
  raise ValidationError(
      "Choose either a page on this site or an external URL (not both)."
  )
  ```

- Shared field groups become abstract mixins (`LinkedCardMixin`), not
  copy-paste.
- Repeating editor content uses `Orderable` + `ParentalKey` + `InlinePanel`,
  always with `max_num` — an unbounded list is an unbounded page.
- `related_name="+"` on foreign keys that need no reverse lookup.

### Editor-facing text is plain language

`help_text` on every field an editor touches, and `verbose_name` wherever the
field name is not self-evident. The audience for this admin is a content
editor, not a Django developer. This is the same plain-language standard the
public site is held to.

### Transitional fields must name their successor

Where a field exists only until a later model lands, the docstring or
`help_text` says so and says what replaces it:

```python
'Comma-separated topic chips shown on the card. Temporary until '
'Knowledge library topics exist.'
```

Without this, temporary scaffolding becomes permanent by default.

### App boundaries

- Models live in the app that owns them.
- `core/` holds shared, model-free code: `navigation.py`, `templatetags/`.
  It has no `models.py` and should not acquire one.
- Navigation is hardcoded in `core/navigation.py`, deliberately — see that
  module's docstring. Add or reorder entries there, **never** in a template.

### Dependencies

Install from `requirements.lock`, never `requirements.txt`. Direct
dependencies with supported ranges go in `requirements.txt`; the lock file is
regenerated from it via `pip freeze`.

---

## C.4. Templates — `DECIDED`

- Shared partials: `aakh/templates/includes/`.
- Page templates: `<app>/templates/<app>/<model>.html`.
- Icons are inlined via `{% icon "name" %}` from `static/icons/`, stored with
  `fill="currentColor"` so they inherit text colour. Never `<img>` an icon
  that needs to respond to a colour scheme.
- **Clean Figma exports before committing an icon.** Figma ships a colour
  overlay as extra stacked paths (`fill="black" fill-opacity="0.8"`, then
  `fill="white" fill-opacity="0.2"`) on top of the `currentColor` path, plus
  `<g id="Vector">` wrappers. The overlay buries `currentColor`, so the icon
  never responds to hover, `aria-current`, or a colour scheme — and duplicate
  `id`s across inlined icons are invalid HTML. An icon file is done when it
  has exactly one `fill="currentColor"` path per shape, no `fill-opacity`,
  and no `id` attributes.
- Exactly one `<h1>` per page, and on an AssetPage it is the first element
  after the breadcrumb — nothing between them (IA B.3.4, B.5).
- Decorative images take `alt=""`; every other image takes descriptive alt
  text. There is no third option.

---

## C.5. Open questions

- `DECIDED` `NOT YET BUILT` — **Dark theme.** `accessibility.md` requires a
  colour-scheme switch. `tokens.css` documents the exact pattern for adding
  one, and the semantic-token contract makes it a single block. But no `theme`
  key exists in `PREF_ATTRS` in `aakh.js`, so nothing is wired up. Trigger:
  before public launch, since it is a stated accessibility requirement.
- `OPEN` — Is a high-contrast scheme a separate theme, or does
  `forced-colors` support suffice?
- `OPEN` — No test suite, linter, or formatter is configured. Decide on
  pytest/ruff before the codebase grows further.
