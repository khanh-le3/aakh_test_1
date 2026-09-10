"""Shared page context and fixed URL behaviour for the knowledge library."""

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, TitleFieldPanel


def library_context(page):
    """Resolve breadcrumbs from the page tree, including unsaved page previews."""
    from .library import KnowledgeLibraryPage

    library = (
        KnowledgeLibraryPage.objects.ancestor_of(page).first()
        if page.path
        else None
    )
    if library is None:
        # Wagtail sets the cached parent before previewing a newly created page.
        parent = getattr(page, "_cached_parent_obj", None)
        if parent is not None:
            library = KnowledgeLibraryPage.objects.ancestor_of(
                parent, inclusive=True
            ).first()
    return {
        "library_page": library,
        "home_page": library.get_parent() if library else None,
    }


def resource_listing_context(page, request, resources):
    context = library_context(page)
    query = request.GET.get("query", "").strip()[:200]
    if query:
        resources = resources.filter(
            models.Q(title__icontains=query)
            | models.Q(full_summary__icontains=query)
            | models.Q(short_summary__icontains=query)
        )
    context.update(
        query=query,
        resources=Paginator(
            resources.select_related("primary_topic")
            .distinct()
            .order_by("-publication_date", "-pk"),
            12,
        ).get_page(request.GET.get("page")),
    )
    return context


class FixedLibraryPathMixin:
    """Keep structural paths stable while allowing editors to update page copy."""

    is_creatable = False
    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug", read_only=True),
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
            ],
            heading="For search engines",
        )
    ]
    content_panels = [TitleFieldPanel("title", targets=[])]

    def clean(self):
        super().clean()
        if self.slug != self.fixed_slug:
            raise ValidationError({"slug": "This page's URL is fixed by developers."})
