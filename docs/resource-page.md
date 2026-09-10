# Resource page

This is the main content page of AAKH. Editor-editable fields are marked [EDITABLE]

## Structure

- Banner
    -- Same treatment as banner in Home and Knowledge Library pages (background color, breadcrumb) 
    -- Breadcrumb should go: Home > Knowledge library > Resource name
    -- Resource name [EDITABLE]: maximum 30 words (also subject to Wagtail's 255-character title limit)
    -- Full summary [EDITABLE]: maximum 150 words
    -- Citation [EDITABLE]: allow editors to specify clickable external links in the admin panel
    -- Metadata: "Type: (snapshot/framework/guideline/report). x minute read. Published month/year. Reviewed month/year"
    Read time supplied by Wagtail Content metrics. Publish and review dates [EDITABLE] selected by editor in admin panel.
    -- Topic(s): Topic chip(s)
- Content
    -- Left panel [EDITABLE]: main content. Allow editors to freely define the structure. It should support up to three levels of headings. Also, the following features should be enabled: bullet list, numbered list, table, quote, link, basic formatting (color, bold, italic, underline), image, video, audio.
    -- Right panel: sticky "On this page" navigation for level 2 and 3 headings, highlighting the topmost visible heading below the main menu

## Metadata:
in admin panel, editor can edit the following metadata for a resource.
- Short summary [EDITABLE]: another shorter summary for Resource cards
- Type [EDITABLE]: snapshot/framework/guideline/report: can only select one, type list predefined by dev (in code?)
- Topic [EDITABLE]: 1 primary topic (mandatory) and max 2 secondary topics (optional), selected from the pre-defined 12 topics
- Keywords [EDITABLE]: editable by content editors, invisible to users

## Editor guide

After running `python manage.py migrate`, open **Pages → Home → Knowledge library → Resources**
in Wagtail and add a **Resource page**. Resources use
`/knowledge-library/resources/<resource-slug>/`. The migration also creates the 12 fixed
topic pages; `/knowledge-library/topics/` redirects to the library. It preserves existing
library copy and creates no example resources.

- Enter a name (30 words), full summary (150 words), and short card summary (40 words).
  The short-summary limit is an implementation default and can be changed in code.
- Choose one of the four resource types, one primary topic, and up to two different
  secondary topics. The topic identities and resource type choices are developer-owned.
- Use the citation editor's link control to link text to the original source.
- Select publication and review dates. The review date is optional until the first review;
  it cannot precede publication. Visitors see the month and year.
- Keywords remain internal, including on resource cards and public search results.
- Add and reorder content blocks. Start section headings at level 2, then use levels 3
  and 4 as needed without skipping a level. Levels 2 and 3 automatically populate
  **On this page**, with level 3 indented under its parent. Level 4 remains in the
  article. Pages without navigation headings omit the contents panel.
- Text blocks support paragraphs, bullet and numbered lists, links, bold, italic,
  underline, and navy/teal text. Colours use site tokens and must not be the only way
  information is conveyed. Headings, quotes, tables, images, video and audio have
  separate blocks; arbitrary HTML and arbitrary text colours are not enabled.
- Tables require a caption and column headings, with one cell per column in every row.
  The first column can also provide row headings. Images require a description or an
  explicit decorative choice; complex images also need a description in the article.
- Each image block has an **Image size** dropdown: **Small** (up to 20rem),
  **Medium** (up to 35rem), or **Full body width** (the default, including existing images).
  These are maximum display widths; images retain their proportions, are not enlarged
  beyond their rendered image dimensions, and shrink to fit narrow screens. Captions
  follow the selected width. Choose full body width for detailed diagrams or text.
- Audio and video use direct HTTP(S) media-file URLs, such as MP3 and MP4, with native
  playback controls. Both require a transcript. Video also requires English WebVTT
  captions and confirmation that the soundtrack describes important visual information.
  Use media hosts that support playback from this site and cross-origin access for video
  and captions. Video-sharing page URLs are not direct media-file URLs.
- Reading time uses Wagtail's Content metrics result from the rendered page preview
  (the same main-content scope used by the editor's Checks panel). The resource
  editor refreshes the preview before saving and stores `extractMetrics(content).readingTime`
  with the revision. Wagtail owns text extraction, language-specific reading speeds
  and rounding; there is no separate Python estimate or minimum-minute override.
  The public page and library cards render the saved value without JavaScript.
  Existing resources need to be saved and published in the editor to gain a metric.
  If the metric is unavailable (including preview failure or an import without a
  metric), read time is omitted rather than guessed. The editor allows saves to
  continue without a metric if preview processing fails or takes over ten seconds.

Drafts and publishing use Wagtail's standard revision and moderation system. Assign the
standard approval workflow and **Content Editors** / **Chief Editors** group permissions
through Wagtail settings; ResourcePage adds no custom workflow.

## Presentation and validation

The banner uses the existing site background and breadcrumbs. Its full summary and citation
extend to the same right content edge as the resource layout. On wide screens the article
is on the left and the contents panel is on the right. Article width is capped at 80ch
using `--resource-content-max-width`, and shrinks to fit narrower screens. On narrow
screens the contents appear above the article. The contents title stays
visible while long contents lists can scroll internally. JavaScript measures the main
menu's height before making it sticky, keeping the contents and heading destinations
clear even when text wraps or accessibility preferences change. Without JavaScript the
main menu remains in normal flow and all fragment links still work. The contents panel
also leaves space for the floating Back to top control. Near the article's end, the
scrollable contents list shortens to keep its title clear of the main menu.

The desktop article column uses up to three quarters of the available column space,
capped at the article's reading width. The contents column receives the remainder,
including any space released by that cap. `--resource-column-gap` controls the gap
between them, defaulting to `--space-lg` (24px).
Level 2 entries in the contents list are bold with `--space-md` (16px) top padding.

As the reader scrolls, the topmost level 2 or 3 heading visible below the main menu receives
`aria-current="location"`, bold text and an accent marker in the contents. Headings covered
by the menu or above the viewport are excluded. If no eligible heading is visible,
no entry is highlighted; level 4 never creates a contents entry. This enhancement does
not change keyboard focus or the page URL. Native media
controls work without JavaScript. Long tables scroll inside a labelled,
keyboard-focusable region.

Topic chips use white text on teal-600, changing to teal-800 on hover, focus and press,
with no underline. The contents panel uses ivory-65 with no visible border, navy-900
link text and teal-600 activated text. Its activated labels are 20px bold so the requested
teal/ivory pairing meets large-text contrast requirements. Links have no underline; the
current entry also has a gold `--color-accent` marker. All markers share the same vertical
axis, while level 3 labels are indented without a vertical connecting line. Keyboard focus
outlines and transparent border fallbacks remain available in forced-colours mode.

The shared heading styles follow [the heading hierarchy reference](design/Resource-page-design.png)
across the site. H2 uses 28–36px bold text, 4rem space before and 1.5rem after; H3 uses
24–28px bold text, 2rem before and 1rem after; H4 uses 20–22px semibold text, 1rem
before and 0.5rem after. Sizes scale with the reader's text settings, and the first
heading in a container does not add leading space. Body text is 18px at the default
setting. Only H2 receives a decorative rule, using `--color-accent`. Compact component
labels, including cards and navigation, retain their component sizing. Home and library
section headings use the shared rule instead of separate accent elements.

Regression coverage is in `knowledge_library/test_resources.py`; run it with
`python manage.py test`. Browser checks cover 320, 768, 1024 and 1440 CSS pixels,
200% text, increased spacing, forced colours, short viewports and JavaScript disabled.
The 320 CSS pixel check also covers the reflow width of a 1280 pixel viewport at 400% zoom.

## PDF download

Each published resource has a `download/` subroute, reached by **Download PDF** below
**On this page**. The contents and download share a sticky desktop sidebar. Narrow
and short windows use normal document flow so the controls cannot obscure the
article. The link works with keyboard navigation and JavaScript disabled, including
resources without headings. Draft previews do not download unpublished edits.

The export uses WeasyPrint 70's tagged PDF/UA-1 output. It includes the resource title,
summary, citation, publication/review dates, topics and full body, plus a link to the
online version. Internal keywords are excluded. The A4 layout uses embedded Lexend,
12pt body text, 1.6 line spacing, generous margins, dark text on white, page numbers,
heading bookmarks and a linked contents list. Text remains selectable. Images retain
alternative text and captions; decorative images are omitted from the PDF's reading
structure while their captions remain. Audio/video become labelled links with full transcripts.
Tables retain column/row headers. Tables wider than four columns become labelled
records to preserve every cell without shrinking the text.

The export route passes through Wagtail's normal live-page routing and inherited
password/login/group restrictions. It additionally rejects unpublished ancestors.
It never reads the latest draft revision. Responses use `private, no-store`; rendered
PDF bytes are internally cached for 15 minutes using a digest of the HTML, styles,
font and images, so publishing changes produces a new export. The PDF renderer can
only read the explicitly registered styles, font and selected image renditions;
resource links cannot trigger arbitrary network requests or local file reads.

Install runtime dependencies with `env/bin/pip install -r requirements.lock`.
WeasyPrint also needs the operating system's Pango, HarfBuzz and font libraries
(available in this development environment). Deployment images must include these;
see [WeasyPrint installation requirements](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).
For the test suite, install `requirements-dev.lock`, which adds the test-only pypdf
reader, then run `env/bin/python manage.py test`.

Tests inspect text, language/title metadata, structure tags, image alternatives,
heading bookmarks, download headers, publication changes and access restrictions.
Tagged output does not itself certify PDF/UA compliance: editorial content and complex
figures/tables still need manual review with a PDF accessibility checker and assistive
technology, as described in [WeasyPrint's PDF/UA guidance](https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html#pdf-ua-universal-accessibility).

Implementation files:

- `knowledge_library/models/resources.py`: Wagtail download route and page context.
- `knowledge_library/resource_pdf.py`: export rendering, media adaptation and asset access.
- `knowledge_library/templates/knowledge_library/resource_pdf.html` and
  `knowledge_library/static/knowledge_library/css/resource-pdf.css`: PDF document and layout.
- `knowledge_library/templates/knowledge_library/resource_page.html`,
  `aakh/static/css/aakh.css` and `aakh/static/js/aakh.js`: download and sticky sidebar.
- `aakh/settings/base.py`: routable-page app registration.
- `requirements.txt`, `requirements.lock`, `requirements-dev.txt` and
  `requirements-dev.lock`: runtime and PDF inspection dependencies.
- `knowledge_library/test_resource_pdf.py`: export regression tests.

## Attachment downloads

Editors can add an **Attachments** block anywhere in a resource's **Body**. Add a
section heading immediately above it to name the group (for example, “Framework” or
“Worksheets”); the existing heading system includes that group in **On this page**.
This follows the grouped title/format/size pattern in the
[Victorian Department of Health example](https://www.health.vic.gov.au/allied-health-workforce/credentialling-competency-and-capability-framework).

In **Attachments → Files**, add one or more files with Wagtail's document chooser.
Editors can upload a new file or select one from Documents, reorder/remove entries,
set an optional download title, and add an optional plain-text description. A blank
title uses the document's title. File format and stored size appear automatically.
Existing document upload formats and limits apply. Editors must check the uploaded
file's accessibility; displaying a download link does not remediate its contents.

Downloads are native links, with visible titles and file metadata, an underlined
link label, a decorative file-down icon, and the shared keyboard focus indicator.
They work without JavaScript and stay in the current browsing context. Empty groups
caused by previously deleted documents do not leave broken links. The generated
resource PDF retains attachment titles, descriptions, file metadata and links;
it does not embed or fetch the attached files.

The attachment list belongs to the page's StreamField, so adding, removing and
reordering attachments follows normal page drafts, revisions and moderation.
Documents themselves use Wagtail's separate collection access permissions. Restricted
download links open that access flow instead of saving a login page. Replacing a
shared document changes the file wherever it is used; upload a new document when
a replacement must be introduced with a later page revision.

Implementation: `knowledge_library/blocks.py`,
`knowledge_library/templates/knowledge_library/blocks/resource_attachments.html`,
`aakh/static/css/aakh.css`, `knowledge_library/resource_pdf.py`,
`knowledge_library/static/knowledge_library/css/resource-pdf.css`, and
`knowledge_library/migrations/0007_resource_attachments.py`.
Regression coverage is in `knowledge_library/test_attachments.py`.
