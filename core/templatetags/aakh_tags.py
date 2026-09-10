"""Shared template tags for the AAKH design system."""
from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe

from core.navigation import resolve_main_menu

register = template.Library()

# Production cache of processed SVG markup, keyed by (name, css_class).
_ICON_CACHE = {}


@register.simple_tag
def icon(name, css_class=""):
    """Inline an SVG icon from static/icons/.

    Icons are stored with fill="currentColor" so they inherit the text colour
    of their surroundings, and with aria-hidden="true" so they are decorative
    by default. Pass meaning through visible text or aria-label on the parent.
    """
    key = (name, css_class)
    # SVG edits do not trigger Django's Python autoreloader. Re-read them in
    # development so changed icon assets appear on the next page request.
    if settings.DEBUG or key not in _ICON_CACHE:
        path = finders.find(f"icons/{name}.svg")
        if path is None:
            return ""  # Unknown icon: render nothing rather than break the page.
        svg = Path(path).read_text()
        classes = f"icon icon--{name}"
        if css_class:
            classes += f" {css_class}"
        # Enforce the decorative contract here rather than trusting every file:
        # raw Figma exports arrive without these and would be exposed to
        # screen readers or land in the tab order.
        attrs = f'class="{classes}"'
        if 'aria-hidden' not in svg:
            attrs += ' aria-hidden="true"'
        if 'focusable' not in svg:
            attrs += ' focusable="false"'
        svg = svg.replace("<svg ", f"<svg {attrs} ", 1)
        _ICON_CACHE[key] = mark_safe(svg)
    return _ICON_CACHE[key]


@register.simple_tag(takes_context=True)
def main_menu(context):
    """The fixed top-level menu, annotated for the current page.

    Use as ``{% main_menu as menu_items %}``. Each entry is a dict with
    ``label``, ``path``, ``icon`` and ``aria_current`` - see core/navigation.py,
    which is the single source of truth for the menu itself.
    """
    request = context.get("request")
    return resolve_main_menu(request.path if request else "")
