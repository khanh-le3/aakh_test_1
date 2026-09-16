from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index

from .block import ContentSectionBlock, TeamSectionBlock

class HomePage(Page):
    """The site home page: hero, featured resources, news and updates."""

    max_count = 1
    parent_page_types = ["wagtailcore.Page"]  # site root only

    # --- Hero ---
    hero_heading = models.CharField(
        "heading first line",
        max_length=120,
        default="Autism research",
        help_text="The start of the main headline, shown in the primary brand colour.",
    )
    hero_heading_line_2 = models.CharField(
        "heading second line",
        max_length=120,
        blank=True,
        default="you can use",
        help_text=(
            "Optional continuation, shown on a new line in the secondary brand colour. "
            "Both parts may wrap further on small screens."
        ),
    )
    # Pylance's Django TextField.__new__ stubs omit Wagtail's valid features kwarg.
    hero_intro = RichTextField(  # pyright: ignore[reportCallIssue]
        features=["bold", "italic", "link"],
        blank=True,
        default=(
            "<p>Welcome to the Australian Autism Knowledge Hub, where we turn "
            "autism research into clear, trustworthy information.</p>"
            "<p>Find out what we know, what we’re still learning, and what it "
            "could mean for you.</p>"
        ),
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
            ],
            heading="Featured resources",
        ),
    ]

class GenericPage(Page):
    """A flexible information page for top-level website content."""

    intro = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        help_text="Short introduction shown below the page title.",
    )

    body = StreamField(
        [
            ("section", ContentSectionBlock()),
            ("team_section", TeamSectionBlock()),
        ],
        blank=True,
        use_json_field=True,
    )

    template = "home/generic_page.html"

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]
