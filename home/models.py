from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page


class LinkedCardMixin(models.Model):
    """A card that links either to a page on this site or to an external URL.

    Exactly one of the two must be set.
    """

    link_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="link to a page on this site",
    )
    link_url = models.URLField(
        blank=True,
        verbose_name="or link to an external URL",
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if bool(self.link_page) == bool(self.link_url):
            raise ValidationError(
                "Choose either a page on this site or an external URL (not both)."
            )

    @property
    def url(self):
        return self.link_page.url if self.link_page else self.link_url


class HomePage(Page):
    """The site home page: hero, featured resources, news and updates.

    The featured-resource and news cards are editor-curated for now. Once the
    Knowledge library (AssetPage) and News (NewsPage) apps exist, these become
    querysets over real pages and the card fields below are retired; the
    templates stay the same.
    """

    max_count = 1
    parent_page_types = ["wagtailcore.Page"]  # site root only

    # --- Hero ---
    hero_heading = models.CharField(
        "heading first line",
        max_length=120,
        default="Autism research you can use",
        help_text="The start of the main headline, shown in the primary brand colour.",
    )
    hero_heading_line_2 = models.CharField(
        "heading second line",
        max_length=120,
        blank=True,
        default="",
        help_text=(
            "Optional continuation, shown on a new line in the secondary brand colour. "
            "Both parts may wrap further on small screens."
        ),
    )
    # Pylance's Django TextField.__new__ stubs omit Wagtail's valid features kwarg.
    hero_intro = RichTextField(  # pyright: ignore[reportCallIssue]
        features=["bold", "italic", "link"],
        blank=True,
        help_text="One or two short paragraphs welcoming visitors.",
    )

    hero_cta_primary_label = models.CharField(
        "primary button label", max_length=40, blank=True, default="Explore the library"
    )
    hero_cta_primary_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="primary button page",
    )
    hero_cta_secondary_label = models.CharField(
        "secondary button label", max_length=40, blank=True, default="About the Hub"
    )
    hero_cta_secondary_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="secondary button page",
    )

    # --- Featured resources ---
    featured_intro = models.TextField(
        blank=True,
        default=(
            "Plain-language research summaries, guidelines and reports - reviewed "
            "by the Olga Tennison Autism Research Centre, with new resources "
            "added regularly."
        ),
        help_text="Short introduction shown under the 'Featured resources' heading.",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_heading"),
                FieldPanel("hero_heading_line_2"),
                FieldPanel("hero_intro"),
                FieldPanel("hero_cta_primary_label"),
                FieldPanel("hero_cta_primary_page"),
                FieldPanel("hero_cta_secondary_label"),
                FieldPanel("hero_cta_secondary_page"),
            ],
            heading="Hero",
        ),
        MultiFieldPanel(
            [
                FieldPanel("featured_intro"),
                InlinePanel("featured_cards", max_num=6, label="Featured resource"),
            ],
            heading="Featured resources",
        ),
        InlinePanel("news_slides", max_num=6, heading="News and updates", label="News item"),
    ]


class FeaturedResourceCard(LinkedCardMixin, Orderable):
    """An editor-curated card in the 'Featured resources' grid (max 6)."""

    home_page = ParentalKey(
        HomePage, on_delete=models.CASCADE, related_name="featured_cards"
    )
    type_label = models.CharField(
        max_length=30,
        help_text='The kind of resource, e.g. "Lay summary", "Guideline", "Report".',
    )
    title = models.CharField(max_length=120)
    summary = models.TextField(
        help_text="One or two plain-language sentences about the resource."
    )
    read_time_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Approximate reading time, in minutes."
    )
    topic_labels = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Comma-separated topic chips shown on the card, e.g. "
            '"early signs, children". Temporary until Knowledge library topics exist.'
        ),
    )

    panels = [
        FieldPanel("type_label"),
        FieldPanel("title"),
        FieldPanel("summary"),
        FieldPanel("read_time_minutes"),
        FieldPanel("topic_labels"),
        FieldPanel("link_page"),
        FieldPanel("link_url"),
    ]

    @property
    def topics(self):
        return [t.strip() for t in self.topic_labels.split(",") if t.strip()]

    def __str__(self):
        return self.title


class NewsSlide(LinkedCardMixin, Orderable):
    """An editor-curated slide in the 'News and updates' carousel."""

    home_page = ParentalKey(
        HomePage, on_delete=models.CASCADE, related_name="news_slides"
    )
    title = models.CharField(max_length=120)
    date = models.DateField()
    summary = models.TextField(
        help_text="One or two plain-language sentences about the news item."
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cta_label = models.CharField(
        "button label", max_length=40, default="Find out more"
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("date"),
        FieldPanel("summary"),
        FieldPanel("image"),
        FieldPanel("cta_label"),
        FieldPanel("link_page"),
        FieldPanel("link_url"),
    ]

    def __str__(self):
        return self.title
