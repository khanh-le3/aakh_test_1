"""Fixed topic pages and the redirect-only topic index."""

from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponseRedirect
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page

from ..topics import TOPIC_ACCENTS, TOPIC_CHOICES
from .shared import FixedLibraryPathMixin, library_context, resource_listing_context


class TopicIndexPage(FixedLibraryPathMixin, Page):
    """A URL segment only: visitors are redirected to topic-first browsing."""

    is_creatable = False
    max_count = 1
    fixed_slug = "topics"
    parent_page_types = ["knowledge_library.KnowledgeLibraryPage"]
    subpage_types = ["knowledge_library.TopicPage"]

    def serve(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.get_parent().url)


class TopicPage(FixedLibraryPathMixin, Page):
    """One of the twelve fixed topics, with editor-owned introduction text."""

    is_creatable = False
    parent_page_types = ["knowledge_library.TopicIndexPage"]
    subpage_types = []
    topic_key = models.SlugField(
        max_length=60, choices=TOPIC_CHOICES, unique=True, editable=False
    )
    introduction = models.TextField(blank=True)
    content_panels = FixedLibraryPathMixin.content_panels + [
        FieldPanel("topic_key", read_only=True),
        FieldPanel("introduction"),
    ]

    @property
    def fixed_slug(self):
        return self.topic_key

    @property
    def accent(self):
        return TOPIC_ACCENTS[self.topic_key]

    def clean(self):
        super().clean()
        if self.topic_key not in dict(TOPIC_CHOICES):
            raise ValidationError("Choose one of the fixed library topics.")
        if self.pk:
            original_key = (
                type(self).objects.filter(pk=self.pk)
                .values_list("topic_key", flat=True)
                .first()
            )
            if original_key is not None and original_key != self.topic_key:
                raise ValidationError("A page's fixed topic cannot be changed.")

    def get_context(self, request, *args, **kwargs):
        from .resources import ResourcePage

        context = super().get_context(request, *args, **kwargs)
        resources = ResourcePage.objects.live().public().filter(
            models.Q(primary_topic=self) | models.Q(secondary_topics=self)
        )
        library = library_context(self)["library_page"]
        if library:
            resources = resources.descendant_of(library)
        context.update(resource_listing_context(self, request, resources))
        return context
