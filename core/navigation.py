"""The site's fixed top-level navigation.

Hardcoded deliberately. The top-level structure is settled (see
.claude/rules/information_architecture.md B.1), so the menu is defined here in
code rather than derived from the Wagtail page tree. That means:

  - the order is fixed and identical on every page (WCAG 3.2.3 Consistent
    Navigation), and cannot be changed by reordering pages in the admin;
  - no database query is needed to render the header or footer;
  - the label, URL and icon of an entry live together in one place.

The trade-off: these paths are NOT checked against the page tree. If a page's
slug changes in Wagtail, update the matching `path` below or the link 404s.

This is the single source of truth for both the header nav and the footer
quick links. Add or reorder entries here, never in the templates.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    """One top-level menu entry.

    label: visible link text.
    path:  absolute URL path, with a trailing slash (Wagtail appends one).
    icon:  file name in static/icons/, without the .svg extension.
    """

    label: str
    path: str
    icon: str


MAIN_MENU = (
    NavItem("Home", "/", "home"),
    NavItem("Knowledge library", "/knowledge-library/", "books"),
    NavItem("News", "/news/", "news"),
    NavItem("About the Hub", "/about-the-hub/", "about"),
    NavItem("Contact us", "/contact-us/", "contact"),
)


def _aria_current(item, current_path):
    """The aria-current value for `item` when viewing `current_path`.

    "page"    this entry IS the current page.
    "true"    the current page sits inside this entry's section, e.g. an asset
              at /knowledge-library/<slug>/ keeps "Knowledge library" marked.
              Orientation matters especially for the Hub's audience, so the
              section stays flagged rather than nothing being marked at all.
    ""        not current; the template then omits the attribute entirely.
    """
    if current_path == item.path:
        return "page"
    # "/" is a prefix of every path, so Home is only ever an exact match.
    if item.path != "/" and current_path.startswith(item.path):
        return "true"
    return ""


def resolve_main_menu(current_path):
    """MAIN_MENU with each entry annotated for the page being rendered."""
    return [
        {
            "label": item.label,
            "path": item.path,
            "icon": item.icon,
            "aria_current": _aria_current(item, current_path),
        }
        for item in MAIN_MENU
    ]
