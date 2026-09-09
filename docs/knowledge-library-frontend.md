# Knowledge library

`/knowledge-library/` is served by Wagtail's `KnowledgeLibraryPage`, in development
and production. Run `python manage.py migrate` to create the model and seed the
page under the site's home page, with all 12 topic cards. The data migration
preserves any existing library page or page already occupying that URL.
The seed migration is irreversible: rolling it back would otherwise leave an
orphaned Wagtail page when the model tables are removed.

## Editing

In Wagtail, open **Pages → Home → Knowledge library**. Editors can change:

- **Banner introduction:** plain text; line breaks are preserved.
- **Browse by topic introduction:** plain text; line breaks are preserved.
- **Topic cards:** choose one of 12 icons, edit the topic name (maximum 60
  characters), and edit the summary (maximum 160 characters).

Cards are revision-aware children of the page, so draft changes remain separate
from published content. Standard Wagtail publishing and moderation apply; no
custom editorial workflow is introduced. Each card shows its fixed topic identity
as a read-only field. Editors can reorder cards, but validation requires exactly
one of each of the 12 developer-owned topics. Changing the display name or icon
does not change the topic identity, reserved URL or colour.
Creating a new library page also preloads the 12 cards.

The starter names follow `AGENTS.md`. “Cross-cutting” remains a working name;
these presentation fields do not decide its eventual resource-assignment rules.

## Cards and colours

The template is `knowledge_library/templates/knowledge_library/knowledge_library_page.html`;
the topic partial is in its `includes/` directory. Styles remain in `tokens.css`
and `aakh.css`. No extra JavaScript, dependency or stylesheet is needed.

All topic cards use ivory-75 (`#ebe5d8`), heading text and body text. Twelve muted
icon accents complement the site palette without repeating its navy, teal or gold:

| Topic | Accent | Hex |
| --- | --- | --- |
| Understanding autism | Plum | `#79537d` |
| Diagnosis and assessment | Terracotta | `#a14f39` |
| Communication, sensory and movement | Rose | `#a4476b` |
| Therapies, supports and services | Sienna | `#a45124` |
| Education and learning | Olive | `#676b36` |
| Work and employment | Periwinkle | `#6863a8` |
| Physical health and healthcare | Brick | `#a14d4a` |
| Mental health and wellbeing | Mauve | `#8a5c73` |
| Family, relationships and social life | Violet | `#7857a0` |
| Daily life and housing | Cocoa | `#805e49` |
| Inclusion, rights and safety | Slate | `#5c6f7e` |
| Cross-cutting | Mulberry | `#944d83` |

The enlarged icon sits to the left of the topic name. Continued lines stay in
the name's column to the right. Icons are 3rem (48px at the default text size),
and can shrink when enlarged text leaves very little room. The grid uses wider
cards, with three columns on a wide desktop. There is no arrow. A single native link wraps the
heading and summary, so the icon, text and surrounding space are all clickable.
Hover, press and keyboard focus darken the background to ivory-100 (`#e3dbcb`)
and underline the name in teal-800.
The grid uses equal fractional rows: all cards match the tallest card, across all
rows, and can grow when text is enlarged. No fixed heights or line truncation
hide editor copy.

Accessibility: each card has one native link labelled by its heading, with a
visible focus outline; icons are decorative. Topic names provide the labels independently
of colour. Cards use list semantics, summaries remain selectable, and borders
preserve boundaries in forced-colours mode. Icon, text and focus colours are
contrast-checked against both the resting and darker card backgrounds.

## Topic icons

The twelve topic assets use the consistent outline style from
[Lucide](https://lucide.dev/), copied from commit
`a537cb6eb323b885f4c60baf3cec1a995982d167`. Only the static SVGs are included;
no JavaScript icon library is installed. The upstream license is retained in
`aakh/static/icons/LICENSE-lucide.txt`. Each SVG uses `currentColor` and is
decorative; the visible topic name provides its meaning.

| Topic | Icon | Lucide source |
| --- | --- | --- |
| Understanding autism | Infinity | `infinity` |
| Diagnosis and assessment | Clipboard with check | `clipboard-check` |
| Communication, sensory and movement | Conversation bubbles | `messages-square` |
| Therapies, supports and services | Helping hands | `hand-helping` |
| Education and learning | Graduation cap | `graduation-cap` |
| Work and employment | Briefcase | `briefcase-business` |
| Physical health and healthcare | Stethoscope | `stethoscope` |
| Mental health and wellbeing | Brain | `brain` |
| Family, relationships and social life | People | `users-round` |
| Daily life and housing | House | `house` |
| Inclusion, rights and safety | Shield with check | `shield-check` |
| Cross-cutting | Connected network | `network` |

Existing editor icon selections use the same keys and do not require a data
migration. Editors can continue choosing a different icon for a card.

## Resource integration

Topic and resource destinations are Wagtail pages. The topics index redirects
to the library and is never linked. Library search opens the resource index,
where it searches resource names and summaries. Recently added lists public,
published resources, ordered by their first publication, with real card metadata
and pagination. Editors can select 20, 50 or 100 items per page using the Apply
button. An empty library shows a plain-language message instead of sample resources.
See [Resource page](resource-page.md) for the editor fields and content blocks.

The original layout came from Figma frame `156:10267`. The repeated topic fixtures
have been replaced by the 12 agreed topics and the requested card appearance.
The banner and the rest of the page retain their existing layout.
Resource summaries and metadata also wrap long words to avoid overflow with
200% text at 320 CSS pixels.
