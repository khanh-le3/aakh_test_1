# Australia Autism Knowledge Hub agent guide
This file contains the authoritative implementation rules for Codex.


## Authority and status

On conflict, precedence is: (1) accessibility, which overrides layout and visual rules; (2) information
architecture (IA), page models, and URLs; (3) code conventions; (4) design system; (5) stack and hosting.
The research bibliography is evidence, not a directive; cite it when justifying decisions or filling a gap.

-`DECIDED`: treat as authoritative.
-`NOT YET BUILT`: do not implement unless the task explicitly reaches the
stated trigger.
-`PROPOSED`: do not treat as an established requirement. Preserve compatibility
with it where inexpensive. Mention material reliance on a proposal in the
final response.
-`OPEN`: do not silently settle the decision. For reversible work, preserve the
existing behaviour or choose an implementation that leaves the decision open.
Ask only when the requested task cannot be completed without resolving the
open decision.

## Project, commands, and layout

AAKH is a public health-information site for an autistic and cognitively disabled audience. It uses Wagtail
7.4/Django, PostgreSQL 16. Hosting is open; Google Cloud Run is only being considered. Prefer
infrastructure independent of La Trobe University services.

```sh
source env/bin/activate
pip install -r requirements.lock
python manage.py runserver
python manage.py makemigrations && python manage.py migrate
podman start aakh-pg  # PostgreSQL 16, host port 55432
```

The venv is `./env` (also pinned in `.vscode/settings.json`). Workflow:
requirements.in / pyproject.toml
        ↓
pip-compile / uv lock
        ↓
deterministic lock

- `aakh/`: settings, base templates, shared static assets. `home/`: `HomePage` and migrations.
- `core/`: shared model-free navigation/template-tag code. `search/`: search view.
- Wagtail docs: `docs/vendor/wagtail-doc-llms-full.md`; search them with `rg`, never load all ~60,000 lines.

## Accessibility (non-negotiable)
Follow ARIA Authoring Practices Guide (APG) https://www.w3.org/WAI/ARIA/apg/
Meet WCAG 2.2 AA and cognitive-accessibility needs. The no-preference, no-JS baseline must itself conform.

- Make all interactions keyboard-operable (Tab, Enter, and arrows as appropriate), expose correct accessible
  name/role/value/state, avoid traps, and use visible, consistent focus indicators.
- Keep navigation clear and consistent; provide skip links. Focus/input must not unexpectedly change context,
  and filter `<select>` elements must not auto-submit.
- Label form fields and provide plain instructions plus clear, preventable, recoverable errors.
- Support text resizing and responsive reflow without clipping, overlap, or two-dimensional scrolling. Test at
  320 CSS px (also the 1280 px/400% zoom case). Use `em` breakpoints so browser font settings affect layout.
- Give meaningful images descriptive alt text and truly decorative images `alt=""`. Caption/transcribe media;
  its controls must work with keyboard and screen readers.
- Avoid time limits or allow extensions. Never autoplay the carousel; honour `prefers-reduced-motion` in CSS.
- Never signal information/state by colour alone. Preserve boundaries under Windows forced colours, including
  transparent-border fallbacks.
- Provide text-size and dark-scheme preferences plus high-contrast support; whether OS forced colours suffice for
  high contrast is open. Offer a dyslexia-friendly font option where possible. Preferences enhance, but never
  create, baseline compliance.

  AAKH website should at least have the following accessibility features:
- **Keyboard navigation:** All interactive elements should be accessible via keyboard (e.g., using Tab, Enter, and Arrow keys).
- **Screen reader support:** All content should be accessible to screen readers, with appropriate ARIA roles and labels.
- **Color contrast:** Ensure sufficient contrast between text and background colors to meet WCAG 2.2 AA standards.
- **Text resizing:** Allow users to resize text without breaking the layout or functionality of the website.
- **Alt text for images:** Provide descriptive alt text for all images, including decorative images that convey meaning.
- **Accessible forms:** Ensure that all form fields have associated labels, and provide clear error messages and instructions.
- **Skip navigation links:** Include skip links to allow users to bypass repetitive content and navigate directly to the main content.
- **Consistent focus indicators:** Ensure that focus indicators are visible and consistent across all interactive elements.
- **Avoiding time-based interactions:** Avoid time limits for completing tasks, or provide options to extend time limits.
- **Accessible multimedia:** Provide captions and transcripts for audio and video content, and ensure that media players are accessible via keyboard and screen readers.
- **Responsive design:** Ensure that the website is usable on various devices and screen sizes, including mobile phones and tablets.
- **Error prevention and recovery:** Provide clear instructions for preventing errors and allow users to easily recover from errors when they occur.
- **Accessible navigation**: Ensure that the website's navigation is clear, consistent, and easy to use for all users, including those with disabilities. 
- **Color schemes and themes**: Provide options for users to switch between different color schemes or themes, including high contrast and dark mode options, to accommodate various visual impairments.
- **Dyslexia-friendly fonts**: Use fonts that are easier to read for users with dyslexia, and provide options to switch to such fonts if possible.

## Information architecture

Use these exact Wagtail-aligned terms:
- **Resource:** one published knowledge unit: Snapshot, Framework, Guideline, or Report. Media is embedded within
  a resource and is never its own resource type.
- **Topic:** one of 12 fixed subject areas. Developers control identities/taxonomy; editors may edit page copy and
  assign assets. Topic-first browsing is the main library entry point; 12 balances specificity against overload.
- **Subtopic:** one editor-owned level below Topic; decided but not built. **Keyword:** internal asset tag, never
  rendered. **Knowledge library:** the whole topic/asset browse-and-search area.

Authoritative Wagtail tree and URLs:
```text
AAKH website
├── Home                                    HomePage
├── Knowledge library                       KnowledgeLibraryPage
│   ├── topics/                             TopicIndexPage    (redirect only, never rendered)
│   │   └── <topic-slug>/                   TopicPage         (12 of these)
│   └── resources/                          ResourceIndexPage (flat listing of all assets)
│       └── <resource-slug>/                ResourcePage      (resource sit HERE, not under a topic)
├── News                                    NewsIndexPage
│   └── <news-slug>/                        NewsPage
├── About the Hub                           GenericPage
└── Contact us                              ContactPage
```
`TopicIndexPage` exists only to form the `topics/` path. It never renders or receives links.
One topic (working name "cross-cutting") may be reserved for high-level assets
that do not belong to any subject topic — typically frameworks, guidelines, and
reports. Not yet confirmed.

TOPICS: 
- Understanding autism
- Diagnosis and assessment
- Communication, sensory and movement
- Therapies, supports and services
- Education and learning
- Work and employment
- Physical health and healthcare
- Mental health and wellbeing
- Family, relationships and social life
- Daily life and housing
- Inclusion, rights and safety
- Cross-cutting

### Resource model — `DECIDED`

| Metadata | Who can edit | Notes |
| Type | ACAMI devs only | Pre-defined and fixed: Snapshot / Framework / Guideline / Report |
| Topics | ACAMI devs only (the topic list); content editors assign | 1 primary (mandatory) + max 2 secondary (optional) per resource |
| Subtopics | Content editors | introduced once a topic accumulates enough assets that browsing it is unwieldy|
| Keywords | Content editors | Internal use only, invisible to end users |

### Editorial workflow

- Editors draft resources and submit to chief editors for approval. Use Wagtail moderation with `Content Editors` and `Chief
  Editors`; no custom workflow code.


## Technical & Coding convention

### CSS and design

- Strict BEM: `block__element--modifier`. In `tokens.css`, keep primitives, semantics, then preference overrides.
  Raw `--aakh-*` values exist only there; components use semantic tokens, never primitives or hard-coded colours.
  Preference overrides target `html[data-a11y-*]`.
- Keep a control's foreground/background rest/hover/active states in one semantic family with a verified `-hover`
  token. Do not borrow families or use `color-mix()`. Add a non-colour cue when state contrast is weak; a separate
  focus indicator may use the contrast-verified `--color-focus` token.
- Preserve load-bearing `aakh.css` order: Base; Utilities; Atoms (`icon`, `btn`, `link-more`, `tag`, `meta`, `input`);
  Molecules (`search-form`, `a11y-options`, `card`, `news-panel`, `subscribe-form`); Organisms (`header`, `site-nav`,
  `hero`, `section`, `carousel`, `footer`). Insert in its numbered section; atoms precede overriding molecules.
- Plain CSS via Django staticfiles only. Raise a project decision before adding npm, a bundler, framework,
  preprocessor, Tailwind, or Sass.
- Mobile is the default. Existing queries: `48em` adds footer columns; `64em` adds two-column hero/news;
  `max-width: 63.99em` is the paired exception moving the news image above text. Keep exceptions rare and paired.
- Civic Theme roles: primary navy `#032059`, secondary teal `#0B7A66`, accent gold `#C9A227`, background ivory
  `#F7F5F0`. Accessibility overrides any unsuitable Civic Theme component.

- Prefer CSS over JavaScript for layout and responsive presentation.
- Avoid fixed viewport-dependent pixel positioning.
- Reuse existing breakpoints/tokens where available.
- Do not introduce dependencies just for small visual effects.
- Do not modify unrelated UI when implementing a scoped design task.

### JavaScript and progressive enhancement

WCAG 2.2 does not require no-JS operation. However, any custom UI component, widget, or interaction built with JavaScript must support keyboard navigation and work with assistive tech. 
Common JavaScript accessibility risks to avoid:
- Keyboard traps: Scripts can prevent users from navigating away from a component using only a keyboard.
- Unexpected context changes: Automatically shifting focus or changing page settings on input without warning violates behavior rules.
- Missing focus management: Dynamic content updates often fail to announce changes to screen readers if ARIA live regions are missing. 

### TechStack 
Wagtail CMS
Hosting: Google Cloud Run
Database: Postgres 16
Images, documents: object storage/CDN
Audio: Cloudflare R2
Video: Cloudflare Stream
Analytics: Self-hosted Umami

### Validation

Before finishing a frontend task:
- run existing lint/test/format commands
- check responsive behaviour
- check for horizontal overflow
- report changed files and remaining visual differences