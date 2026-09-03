# B. Information architecture — AAKH website (Stage 1)

**Purpose of this document.** It defines the site structure, page layouts, content
model, and URL/page-model decisions for the Australia Autism Knowledge Hub. Read
it alongside `.claude/rules/accessibility.md` (accessibility requirements, which
override any layout suggestion here) and `.claude/rules/design_system.md`.

**Status labels.** Every statement carries one:

| Label | Meaning |
|---|---|
| `DECIDED` | Settled. Do not re-litigate; implement as written. |
| `PROPOSED` | Intended, but not yet confirmed. Flag before building on it. |
| `OPEN` | Unresolved. Ask before assuming an answer. |

Anything in Stage 1 is subject to change during development; the labels record
how settled each piece currently is.

**Settled is not the same as scheduled.** A decision can be `DECIDED` and still
not be in the first release. Where that applies it carries `NOT YET BUILT`
alongside, together with the trigger that brings it into scope.

---

## B.0. Terminology

Use these terms exactly. They map 1:1 to Wagtail page models.

| Term | Meaning |
|---|---|
| **Asset** | A unit of published knowledge. Exactly four types: Snapshot, Framework, Guideline, Report. |
| **Topic** | One of 12 fixed subject areas. Editable by ACAMI devs only, not by content editors. |
| **Subtopic** | A finer division within a topic, one level below Topic. Owned by content editors. `DECIDED` `NOT YET BUILT` — see B.6. |
| **Keyword** | Internal-only tag on an asset. Never rendered to end users. |
| **Knowledge library** | The whole browse-and-search section containing topics and assets. |

**Media is not an asset.** Video and audio are delivery mechanisms *within* an
asset, never standalone content types. `DECIDED`

---

## B.1. Site structure / sitemap

`DECIDED` — the page tree below is authoritative. Where it conflicts with any
older diagram, this one wins.

```
AAKH website
├── Home                                    HomePage
├── Knowledge library                       KnowledgeLibraryPage
│   ├── topics/                             TopicIndexPage    (redirect only, never rendered)
│   │   └── <topic-slug>/                   TopicPage         (12 of these)
│   ├── assets/                             AssetIndexPage    (flat listing of all assets)
│   └── <asset-slug>/                       AssetPage         (assets sit HERE, not under a topic)
├── News                                    NewsIndexPage
│   └── <news-slug>/                        NewsPage
├── About the Hub                           GenericPage
└── Contact us                              ContactPage
```

**Note the asymmetry, it is intentional:** topic pages are nested under
`topics/`, but asset pages are *not* nested under `assets/`. Assets are direct
children of Knowledge library so their URLs stay short and citable. See B.4.

---

## B.2. Global chrome

### Header — `DECIDED`

Two rows:

1. **Top row:** logo, site-wide search.
2. **Bottom row (sticky):** navigation menu, accessibility options button.

The accessibility options button opens user-adjustable display preferences. It
must exist from the first build, not be retrofitted — every component has to
respond to it.

### Footer — `DECIDED`

Contains, in no fixed order yet:

- Quick links
- Connect with us / social media links
- Logo
- Subscribe
- Acknowledgement of funder, country, and website builder
- "Part of OTARC" acknowledgement
- Copyright, Disclaimer, Privacy, Accessibility statement, Sitemap

---

## B.3. Page layouts

Each list is top-to-bottom rendering order.

### B.3.1. Home — `DECIDED`

1. Hero: key message + 2 CTA buttons ("Explore the library", "About the Hub")
2. Featured resources
3. News and updates

### B.3.2. Knowledge library — `DECIDED`

1. Banner: breadcrumb; title + intro; search the library
2. Browse by topics: 12 topic tiles, plus a "View all assets" link → `/knowledge-library/assets/`
3. Recently added assets

### B.3.3. Topic page — `DECIDED`

Reached by clicking a topic tile on the Knowledge library page, or a topic chip
on an asset page.

1. Banner: breadcrumb; title + intro; search within this topic
2. Body, two columns:
   - **Left:** side navigation listing all 12 topics
   - **Right:** filter by asset type (All / Snapshot / Framework / Guideline / Report), then the list of assets

The 12-topic sidebar is why a separate "all topics" index page is unnecessary —
see B.4.

### B.3.4. Asset page — `DECIDED`

Reached by clicking an asset card.

1. Banner:
   - Breadcrumb
   - `<h1>` title
   - Summary
   - Topic chips (see B.5)
   - Citation
   - Metadata: read time, publish date, review date
2. Body, two columns:
   - **Left:** "on this page" side navigation
   - **Right:** content organised into numbered headings

Ordering constraint: the `<h1>` must be the first thing after the breadcrumb.
Nothing — including topic chips — goes between them. See B.5 for why.

---

## B.4. Knowledge library: URL structure and page models

### B.4.1. URLs — `DECIDED`

```
/knowledge-library/                      KnowledgeLibraryPage   landing
/knowledge-library/topics/               TopicIndexPage         redirect only, never rendered
/knowledge-library/topics/<topic-slug>/  TopicPage              12 of these, fixed
/knowledge-library/assets/               AssetIndexPage         listing only
/knowledge-library/<asset-slug>/         AssetPage              flat + short, for citation
```

### B.4.2. Why assets are flat, not nested under their topic — `DECIDED`

Asset URLs appear in academic reference lists and must not break. Nesting them
under a topic slug (`/topics/<topic>/<asset>/`) means a topic rename, or an
asset being re-categorised, breaks every published citation. Flat wins.

### B.4.3. Why TopicIndexPage exists but is never rendered — `DECIDED`

Wagtail derives URLs from the page tree, so `/knowledge-library/topics/<slug>/`
requires *some* page at `/knowledge-library/topics/`.

But that page has no content to show. The 12 topics already appear as tiles on
KnowledgeLibraryPage (B.3.2) and as a sidebar on every TopicPage (B.3.3). A
third identical list would be a page that looks near-identical to the library
landing page — and two near-identical pages destroy orientation for
cognitively disabled and autistic users. See `.claude/rules/references.md`.

So it exists structurally and is invisible:

- `serve()` returns a redirect to its parent (KnowledgeLibraryPage)
- `get_sitemap_urls()` returns `[]`
- `show_in_menus_default = False`
- Use `permanent=False` (302) until the IA is final — browsers cache 301s hard

Since adopting topic chips (B.5), **nothing anywhere links to this page.** Its
redirect is now purely a safety net for hand-typed or previously-indexed URLs.

**Do NOT use `RoutablePageMixin` to avoid creating this page.** TopicPages must
remain real Wagtail pages: editors edit their intro text, and they need
revisions, preview, the moderation workflow, and search indexing.

### B.4.4. Asset model — `DECIDED`

| Field | Implementation | Notes |
|---|---|---|
| `type` | Django `TextChoices` | Snapshot / Framework / Guideline / Report. Fixed, dev-editable only — so not a snippet. |
| `primary_topic` | Required FK to TopicPage | Must be an explicit field. It is **not** derivable from the parent page, because assets are flat. |
| `secondary_topics` | `ParentalManyToManyField` to TopicPage | Max 2, enforced in `clean()`. Optional. |
| `keywords` | `ClusterTaggableManager` (django-taggit) | Internal only. Never rendered in templates. |
| `subtopic` | Optional FK, **not in the initial model** | `DECIDED` `NOT YET BUILT`. Design AssetPage so that adding it later is a plain additive migration — do not foreclose it, do not build it yet. |

**One AssetPage model, not four page types.** This makes "filter by asset type"
(B.3.3) a single ORM filter, and gives editors one consistent editing form.

### B.4.5. Tree constraints — `DECIDED`

- Set `parent_page_types` / `subpage_types` on every model, so editors
  physically cannot create a page in the wrong place. This is a guardrail
  editors feel in the admin, not a rule they must remember.
- `max_count = 1` on KnowledgeLibraryPage, TopicIndexPage, AssetIndexPage.
- Wagtail already enforces unique slugs among siblings, so `topics` and
  `assets` are automatically unavailable to an AssetPage. No extra validation
  needed — but the error an editor sees if they try is unhelpful, so consider a
  clearer `clean()` message.

---

## B.5. Breadcrumbs and topic chips — `DECIDED`

### Breadcrumbs

**Every page type, including AssetPage, derives its breadcrumb purely from
Wagtail page ancestry.** One template, no special cases. On an asset that gives:

```
Home > Knowledge library > <Asset title>
```

**Do NOT build a synthetic breadcrumb that injects the primary topic.** Two
reasons it was rejected:

1. It would contain a "Topics" crumb pointing at TopicIndexPage, which
   redirects to Knowledge library — a link whose label does not match where it
   lands. That is the exact orientation failure B.4.3 exists to prevent.
2. An asset has up to 3 topics. A breadcrumb is a single linear path, so naming
   the primary topic misrepresents the route taken by anyone who arrived from a
   *secondary* topic.

### Topic chips

Topic context is carried by chips instead of by the breadcrumb.

- **Placement:** in the asset banner, *after* the `<h1>` and summary, grouped
  with the citation/metadata block. **Not** between the breadcrumb and the
  title. The `<h1>` is the strongest orientation signal on the page and must
  land first — putting three links ahead of it delays "what is this page?" for
  screen reader users and adds cognitive load for everyone.
- **Visible group label:** e.g. `Topics:` or `This asset appears in:`. Never a
  bare floating row of pills.
- **Deterministic order:** primary topic first, then secondaries in a fixed
  order, so the same asset always presents its topics identically.
- **Do not visually distinguish primary from secondary.** That distinction is
  an editorial/IA concern, not something the reader needs.

Each chip links to its TopicPage (`/knowledge-library/topics/<topic-slug>/`).

---

## B.6. Content model rationale

### Entry point — `DECIDED`

The main entry point to the knowledge library is **by topic**, as the most
intuitive route for a lay audience.

### The 12 topics — `DECIDED`

Twelve is a deliberate balance: not so few that topics are uselessly broad, not
so many that the tile grid overwhelms, and broad enough to cover autism
research.

Topics are pre-defined and fixed. **Editable by ACAMI devs only, never by
content editors.**

### Cross-cutting topic — `PROPOSED`

One topic (working name "cross-cutting") may be reserved for high-level assets
that do not belong to any subject topic — typically frameworks, guidelines, and
reports. Not yet confirmed.

### Conceptual hierarchy

This is the *logical* grouping of content. It is **not** the page tree or the
URL structure — for those, see B.1 and B.4.1.

```
Knowledge library
├── Topic 1
├── Topic 2
│   ├── Subtopic 1: Asset #x          (subtopics NOT YET BUILT)
│   └── Subtopic n
├── ...
└── Topic 12: Asset #x
```

### Asset metadata — `DECIDED`

| Metadata | Who can edit | Notes |
|---|---|---|
| Type | ACAMI devs only | Pre-defined and fixed: Snapshot / Framework / Guideline / Report |
| Topics | ACAMI devs only (the topic list); content editors assign | 1 primary (mandatory) + max 2 secondary (optional) |
| Subtopics | Content editors | `DECIDED` `NOT YET BUILT` — the design is settled; introduce it only once a topic accumulates enough assets that browsing it is unwieldy. At ~1 snapshot/week that is a long way off. |
| Keywords | Content editors | Internal use only, invisible to end users |

---

## B.7. Editorial workflow — `DECIDED`

Content editors draft assets, then send them to chief editors for approval.

Implement with Wagtail's built-in moderation workflow plus two groups —
`Content Editors` and `Chief Editors`. No custom code required.

---

## B.8. Open questions

- `OPEN` — Are TopicPage slugs stable enough to appear in a public URL at all?
- `OPEN` — Read time: computed from word count, or entered by editors?
- `OPEN` — Footer element ordering.
- `PROPOSED` — Whether the "cross-cutting" topic is adopted, and its final name.
