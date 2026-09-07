# Replace the existing AAKH homepage hero illustration

Implement this change in the current repository. This is a replacement of the existing homepage hero illustration, not an additional illustration, a standalone demo, or a homepage redesign.

## 1. Inspect the existing implementation first

Read applicable AGENTS.md instructions. Locate the homepage template, hero partial/component, current illustration markup, associated styles, static-asset handling, design tokens, accessibility settings, and relevant tests/build commands.

Use the project's existing Wagtail/Django and frontend conventions. Do not introduce React, Tailwind, a new icon package, or another framework. Scope changes to this hero and the minimum supporting layout/styles. Do not edit Figma.

Preserve the existing header/navigation, hero headline and introductory copy, both CTA labels and URLs, CMS bindings for that content, and all subsequent homepage sections. Do not copy extra taglines, institutional logos, or other page content from earlier mock-ups.

Remove the old illustration from the rendered hero, including any separate mobile rendition and obsolete hero-only decorative styling. Do not merely hide it behind the new composition. Do not delete shared assets, remove CMS fields, or create migrations for this visual replacement. Keep the outer hero background/divider unchanged unless a small, clearly explained integration adjustment is necessary.

## 2. Assets and references

These assets already exist in the repository:

- aakh/static/img/hero/research-paper.svg
- aakh/static/img/hero/arrow-evidence.svg
- aakh/static/img/hero/arrow-understanding.svg

Inspect their viewBox, intrinsic dimensions, whitespace and appearance before positioning them. Preserve aspect ratios. The research-paper artwork may already contain the intended tilt, paper stack and shadows: do not add a second rotation or duplicate these effects without inspecting it.

Reuse these SVGs; do not redraw the research paper, generate a replacement image, or flatten the composition. Resolve their URLs through the existing Django static mechanism, normally {% static 'img/hero/research-paper.svg' %}, rather than using the repository path as a browser URL.

Figma references, when accessible through available Figma tools:

Desktop:
https://www.figma.com/design/8dBzmRFnYZuI2jsLZxPTNi/AAKH--Website?node-id=590-2686

Mobile:
https://www.figma.com/design/8dBzmRFnYZuI2jsLZxPTNi/AAKH--Website?node-id=591-2680

Use the supplied screenshots (docs/design/Desktop.png, docs/design/Mobile.png) when direct Figma access is unavailable. Screenshots are design references only, never production image assets. The desktop reference is an 880 x 720 illustration component, NOT the full hero or a required production size. The mobile reference is 390 x 790; its height is not a fixed implementation requirement.

## 3. Build one responsive SVG + HTML/CSS component

Create a reusable template partial/component following repository conventions, then insert it where the homepage currently renders its illustration. Use scoped selectors, such as .aakh-hero-visual, or the project's equivalent naming convention.

Separate it into:

A. Decorative background: CSS mint field, gold circle, teal circle and dot pattern.
B. Evidence group: HTML label, research-paper SVG and evidence-arrow SVG.
C. Understanding group: HTML label, understanding-arrow SVG and an HTML summary panel.

Use one set of meaningful HTML content for all breakpoints, not duplicated desktop/mobile text.

The entire composition is non-clickable. Do not add links, buttons, click handlers, pointer cursors, hover-lift effects, animation, parallax or new keyboard stops. The existing hero CTA buttons remain unchanged.

## 4. Visual treatment

Reproduce the reference's research-paper-to-clear-summary composition, with restrained navy typography, pale mint background, small gold/teal accents and subtle depth. Avoid a generic oval behind the artwork.

Reuse existing colour and typography tokens. Brand references are navy #032059, teal #0B7A66, gold #C9A227 and warm ivory #F7F5F0. Use a pale mint tint matching the reference. Use the existing site font, Lexend where configured, including existing accessibility font overrides; do not introduce handwritten lettering or another font download.

Build the mint background as a separate CSS layer with an asymmetric, broad curved/angled edge. Circles should be CSS shapes; the dots should be a small tiled radial-gradient patch. Keep these layers independently positioned and behind the foreground. Clip only the decoration layer when necessary, not readable content or focus outlines. Decorations must not block pointer events.

Build the ENTIRE summary panel in HTML/CSS: surface, border, corner radius, subtle shadow, padding, heading, short teal rule and explanation rows. Its height must grow with its text. Do not place text over an exported, fixed-size panel background.

Use the project's existing outline icons for people, lightbulb and leaf, if available. Otherwise use simple local inline SVG equivalents without adding a package. Place them on small pale coloured CSS discs. They are explanatory decorations, not controls; do not use emoji.

At normal text settings, target roughly 1rem summary body text with a comfortable line height; labels around 1.125–1.375rem and the summary headline around 1.5–1.625rem are starting points, not fixed requirements. Preserve readability and hierarchy instead of shrinking text to fit the image slot.

## 5. Layout, alignment and responsive behaviour

Use CSS Grid/Flexbox for meaningful content, with labels and panels in normal flow. Keep each label in the same logical group as the artwork/panel it describes. Use local positioned wrappers for arrows and decorative offsets, not viewport-level coordinates.

Do not copy all Figma x/y coordinates into absolute-positioned HTML. Do not use transform: scale() on the complete component, a canvas, SVG foreignObject, a fixed-height scene, or JavaScript positioning to fit it into the hero.

Wide visual container:
- Evidence/paper group on the left and summary group on the right.
- “From research evidence” sits above/near the paper; the small evidence arrow points towards the paper.
- “To clearer understanding” sits above the summary; the understanding arrow visually connects the two stages.
- Keep the slight overlap/depth suggested by the reference without covering text.
- Put the gold circle near the paper's upper edge, teal circle behind the summary's upper-right edge, and a modest dot patch near its lower-right edge.

Narrow visual container:
- Use the mobile reference's compact paper-and-label arrangement above the summary.
- Let the summary use the available width, with wrapping text and content-driven height.
- Hide the dots and teal circle; retain a restrained gold accent.
- Hide the evidence arrow when crowded. Reposition/rotate the understanding arrow where it still communicates the sequence, or hide it rather than allowing collisions.
- On narrow page layouts, put the visual after the existing hero copy and CTAs.

IMPORTANT: Respond to the visual's actual available column width, not just the browser width. A wide browser can still give this component a narrow hero column. Use container queries where compatible with the project, or suitable layout breakpoints. Conservatively adjust the hero column proportions or stack earlier when necessary. Do not squeeze the 880px reference into the old image slot by scaling everything down. Do not widen the entire site's content grid to make it fit.

Use rem-based typography, flexible gaps, min-width: 0 where needed, and auto-sized content. Allow natural line wrapping rather than forcing every Figma line break. Do not hide overflow on the page to conceal a layout problem. Maintain a logical reading order when the CSS layout changes.

## 6. HTML text and editorial status

Use these labels exactly:

From research evidence
To clearer understanding
Plain-language summary

The current Figma example contains the following ILLUSTRATIVE, UNVERIFIED copy. Reproduce it for this development/design implementation, retaining the visible disclosure below. Do not treat it as an approved research finding, invent a citation, or deploy it as approved production content.

Summary headline:
Inclusive school environments can improve wellbeing for Autistic young people

Explanation rows:
1. Supportive school environments are associated with better mental health.
2. Simple, practical changes can make a difference.
3. Inclusion benefits all students.

Visible disclosure:
Illustrative copy only

Keep this copy together in the component or its existing content mechanism so it is easy to replace. Add a concise editorial TODO requiring approved replacement copy before release. Do not create new CMS models for this task. This example text does not replace the existing introductory hero copy.

## 7. Accessibility and robustness

Keep labels and summary text selectable, real HTML, with suitable heading/list semantics. Do not mark the entire component aria-hidden or give it role="img" in a way that hides its readable descendants.

Use alt="" for decorative SVGs included via img. Hide decorative inline icons and decoration-only wrappers from assistive technologies. Do not duplicate the visible summary in a large aria-label. Do not apply pointer-events: none to the readable text container.

Respect existing colour/contrast and text-size/font controls. Keep content readable under increased text size, altered text spacing and any existing high-contrast/forced-colour treatment. Do not add motion. Reserve sensible space for SVGs using their actual aspect ratios without imposing a fixed height on the whole composition.

## 8. Validate in the real homepage and report

Run the relevant existing checks/build/tests. Verify the homepage rather than only an isolated demonstration page.

With available browser tooling, inspect at 320, 390, 768, 1024, 1440 and 1920px viewport widths, including widths where the hero column is narrower than expected. Test 200% text enlargement, 400% browser zoom/reflow, and the site's existing accessibility options. Test increased text spacing: line height 1.5, paragraph spacing 2em, letter spacing 0.12em and word spacing 0.16em.

Check that the old illustration is gone; assets load; copy/CTAs are preserved; there are no collisions, clipped text or unintended horizontal scrolling; the summary grows; and the visual has no interactive affordances or keyboard stops. Compare desktop/mobile browser screenshots with the references and correct significant differences. Report tools or checks that could not run; do not claim unperformed validation or complete WCAG compliance.

Finish with the files changed, how the replacement is integrated, responsive decisions, tests actually performed, remaining visual differences and the editorial release blocker. Do not deploy, publish, push or make unrelated changes.

Proceed with repository inspection, implementation and validation; do not stop after producing a plan.
