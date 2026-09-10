"""Render resource headings and navigation together, without browser scripting."""

from django.utils.html import format_html, format_html_join
from django.utils.text import slugify

from .blocks import HEADING_LEVELS


def resource_content_context(body):
    """Return safe rendered content and a matching nested table of contents."""
    rendered = []
    toc = []
    parents = []
    used_ids = set()
    for index, block in enumerate(body):
        level = HEADING_LEVELS.get(block.block_type)
        if level is None:
            rendered.append(block.render(context={"resource_block_id": f"resource-block-{index + 1}"}))
            continue

        title = str(block.value)
        stem = f"resource-section-{slugify(title, allow_unicode=True) or 'section'}"
        anchor = stem
        suffix = 2
        while anchor in used_ids:
            anchor = f"{stem}-{suffix}"
            suffix += 1
        used_ids.add(anchor)
        if level in {2, 3}:
            heading = {"title": title, "text": title, "id": anchor, "level": level, "children": []}
            while parents and parents[-1]["level"] >= level:
                parents.pop()
            (parents[-1]["children"] if parents else toc).append(heading)
            parents.append(heading)
        rendered.append(format_html(
            '<h{level} class="resource-content__heading" id="{anchor}" tabindex="-1">{title}</h{level}>',
            level=level, anchor=anchor, title=title,
        ))

    return {
        "resource_body": format_html_join("\n", "{}", ((part,) for part in rendered)),
        "resource_toc": toc,
    }
