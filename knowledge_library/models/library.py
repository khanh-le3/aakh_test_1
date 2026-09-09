"""Knowledge library landing page and its topic cards."""

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.models import Orderable, Page

from ..panels import TopicCardsPanel, validate_topic_keys
from ..topics import BANNER_INTRO, ICON_CHOICES, TOPIC_CHOICES, TOPIC_COUNT, TOPICS_INTRO

if TYPE_CHECKING:
    from django.db.models import Manager


class KnowledgeLibraryPage(Page):
    """Topic-first entry point for the knowledge library."""

    # Page supplies standard features such as a title, URL slug, drafts and publishing.
    # The TopicCard.page relationship below creates topic_cards automatically;
    # this annotation only tells the type checker what that collection contains.
    if TYPE_CHECKING:
        topic_cards: Manager["TopicCard"]

    # Wagtail reads these settings when deciding which pages editors can create.
    # Allow only one page of this type across the page tree (not a database limit).
    max_count = 1
    # Resources have a flat parent; topic pages provide a separate browse route.
    parent_page_types = ["home.HomePage"]
    subpage_types = [
        "knowledge_library.TopicIndexPage",
        "knowledge_library.ResourceIndexPage",
    ]

    # Fields define data stored for each page. TextField holds longer text;
    # the first argument is its editor label, default supplies initial content,
    # and help_text gives instructions in the editing form.
    banner_intro = models.TextField(
        "banner introduction",
        default=BANNER_INTRO,
        help_text="A short introduction to the knowledge library. Use plain text.",
    )
    topics_intro = models.TextField(
        "Browse by topic introduction",
        default=TOPICS_INTRO,
        help_text="A short paragraph helping visitors choose a topic. Use plain text.",
    )

    # Panels arrange the Wagtail editing form, not the public webpage layout.
    # Keep the standard page controls, then add our fields. FieldPanel displays
    # one field; MultiFieldPanel groups controls under a shared heading.
    content_panels = Page.content_panels + [
        FieldPanel("banner_intro"),
        MultiFieldPanel(
            [
                FieldPanel("topics_intro"),
                # Our custom panel (in panels.py) edits the related cards within
                # this page's form. Equal minimum/maximum counts require 12 cards;
                # its validation also checks that every fixed topic appears once.
                TopicCardsPanel(
                    "topic_cards",
                    label="Topic card",
                    min_num=TOPIC_COUNT,
                    max_num=TOPIC_COUNT,
                    help_text=(
                        "Edit the icon, name and summary for each of the 12 topics. "
                        "Topic identities and their destinations are fixed. "
                        "Names allow 60 characters; summaries allow 160 characters."
                    ),
                ),
            ],
            heading="Browse by topic",
        ),
    ]

    def clean(self):
        # clean() is a validation hook used by Django/Wagtail forms. Calling super()
        # retains the inherited checks. A direct model save() does not call clean().
        super().clean()
        # pk is the record's primary key (database ID).
        # A newly inserted page may receive its children immediately afterwards.
        # Existing pages, including revisions, must retain the fixed topic set.
        if self.pk:
            # .all() gets the related cards; the helper checks their topic identities.
            validate_topic_keys([card.topic_key for card in self.topic_cards.all()])

    def get_context(self, request, *args, **kwargs):
        from .resources import ResourcePage

        context = super().get_context(request, *args, **kwargs)
        per_page = {"20": 20, "50": 50, "100": 100}.get(
            request.GET.get("per_page", "20"), 20
        )
        recent_resources = (
            ResourcePage.objects.descendant_of(self)
            .live()
            .public()
            .select_related("primary_topic")
            .order_by("-first_published_at", "-pk")
        )
        paginator = Paginator(recent_resources, per_page)
        recent_page = paginator.get_page(request.GET.get("page"))
        context["recent_resources"] = recent_page
        context["recent_per_page"] = per_page
        context["recent_page_sizes"] = (20, 50, 100)
        context["recent_page_range"] = list(
            paginator.get_elided_page_range(recent_page.number, on_each_side=1, on_ends=1)
        )
        return context


class TopicCard(Orderable):
    # Each card is a stored record. Orderable supplies a sort_order field so cards
    # can be retrieved in their configured display order.
    # ParentalKey links a card to its page and lets Wagtail save the cards together
    # with page drafts/revisions. CASCADE deletes cards when their page is deleted.
    # related_name enables the reverse lookup: page.topic_cards.all().
    page = ParentalKey(
        KnowledgeLibraryPage, on_delete=models.CASCADE, related_name="topic_cards"
    )
    # A slug is a URL-friendly identifier, such as "understanding-autism".
    # This fixed identity is separate from the name editors can change. choices
    # lists allowed values; editable=False excludes it from editable form fields.
    topic_key = models.SlugField(
        "fixed topic",
        max_length=60,
        choices=TOPIC_CHOICES,
        editable=False,
    )
    # CharField stores short text with a length limit. The icon field stores an
    # identifier from ICON_CHOICES, not the image itself.
    name = models.CharField(
        "topic name", max_length=60, help_text="Maximum 60 characters."
    )
    summary = models.CharField(
        max_length=160, help_text="One short sentence. Maximum 160 characters."
    )
    icon = models.CharField(max_length=30, choices=ICON_CHOICES)

    # Controls shown for each card inside the page editor; its identity is read-only.
    panels = [
        FieldPanel("topic_key", read_only=True),
        FieldPanel("icon"),
        FieldPanel("name"),
        FieldPanel("summary"),
    ]

    class Meta(Orderable.Meta):
        # Meta holds model configuration. Inherit Orderable's ordering settings
        # and add a database rule: a page cannot have two cards for the same topic.
        constraints = [
            models.UniqueConstraint(
                fields=["page", "topic_key"], name="unique_library_topic_card"
            )
        ]

    def clean(self):
        # Reject unknown topic identities and changes to an existing card's identity.
        # ValidationError reports a problem to the form so the editor can correct it.
        super().clean()
        if self.topic_key not in dict(TOPIC_CHOICES):
            raise ValidationError("Choose one of the fixed library topics.")
        if self.pk:
            # objects is Django's database query interface. Find the saved card by
            # ID and read only its topic_key; first() returns None if no row exists.
            original_key = (
                type(self).objects.filter(pk=self.pk)
                .values_list("topic_key", flat=True)
                .first()
            )
            if original_key is not None and original_key != self.topic_key:
                raise ValidationError("A card's fixed topic cannot be changed.")

    @property
    def icon_name(self):
        # A property is accessed like a field (card.icon_name), but calculated on
        # demand rather than stored. This produces the template's icon asset name.
        return f"topic-{self.icon}"

    @property
    def url(self):
        # TopicPage uses the same developer-owned identity and reserved URL.
        return f"{self.page.url or '/knowledge-library/'}topics/{self.topic_key}/"

    def __str__(self):
        # Use the readable card name when Python/Wagtail displays this record as text.
        return self.name
