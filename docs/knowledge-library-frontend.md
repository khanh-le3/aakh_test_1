# Knowledge Library frontend

With the development server running, open `/knowledge-library/`. This preview
route is available only when `DEBUG=True` and renders the existing site header,
footer and accessibility controls. It adds no Wagtail models, migrations or data.

The template is `knowledge_library/templates/knowledge_library/knowledge_library_page.html`.
The `knowledge_library` Django app is registered alongside `home`, ready for
Wagtail models to be added later.
It uses `tokens.css` and `aakh.css`, with card partials in the adjacent `includes/`
directory. No additional stylesheet or JavaScript is required.

Reference: [Knowledge Library, Figma frame 156:10267](https://www.figma.com/design/8dBzmRFnYZuI2jsLZxPTNi/AAKH--Website?node-id=156-10267).
The layout includes the visible banner, topic grid, recent resources and pagination.
Sections hidden in the mockup are omitted. The existing semantic colours and
shape tokens take precedence over new topic-specific palettes. Topic icons are
unchanged Figma SVG exports. The banner uses an export of the Figma background;
the existing Uluru texture asset was fully transparent.

All content is a static design fixture. In particular, the third topic row repeats
the second row as in Figma; it does not define the remaining topic identities.
Read times, review dates, resource copy and pagination are sample content.
The future topic taxonomy, resource content and real page counts still need to
replace these fixtures. The search hint does not promise spelling correction.

Search and resource/topic destinations use the agreed future library URLs, which
are not implemented yet. Pagination and page-size submission also await integration;
the preview always renders the same sample page. The page-size select has an explicit
Apply button so selecting an option never submits automatically.

Accessibility patterns include one H1, labelled search with persistent help,
named navigation regions, semantic card lists and resource metadata, one title
link per card, decorative images, and the existing keyboard focus indicators.
Cards reflow without fixed heights or clipped summaries.

Two shared accessibility fixes found during preview checks allow the footer's
acknowledgement text to wrap below its flags and let navigation scroll away in
short viewports, including the 320 × 256 CSS pixel case at 400% zoom.
