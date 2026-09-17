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

def default_about_body():
    return [
        (
            "section",
            {
                "heading": "About us",
                "body": (
                    "<p>We know that a lot of great Autism research "
                    "is published every year. But finding it, "
                    "understanding what it means, and knowing how "
                    "to use it in your everyday life isn't always "
                    "easy. The Australian Autism Knowledge Hub has "
                    "been designed to make that easier for everyone.</p>"

                    "<p>Here, you can find clear, useful information "
                    "and resources that bring together autism research, "
                    "lived experience and community knowledge. "
                    "Everything on the Hub is free.</p>"

                    "<p>Whether you're Autistic, a family member, "
                    "researcher, practitioner, service provider or "
                    "policymaker, you can use the Hub to explore "
                    "what we know, what we're still learning, and "
                    "what Autism research could mean for you and "
                    "your community.</p>"

                    "<p>The Hub has been created with, not just for, "
                    "the Autistic and autism communities. Autistic "
                    "people, families and community organisations "
                    "have helped to decide what we focus on, and "
                    "they will keep shaping how we make sense of "
                    "research, how we turn it into something useful "
                    "and how we share it with you and the broader "
                    "community.</p>"
                ),
            },
        ),

        (
            "section",
            {
                "heading": "What you'll find here",
                "body": (
                    "<p>We want to make autism research easier "
                    "for you to find, understand and use.</p>"

                    "<p><b>Through the Hub, you can:</b></p>"

                    "<ul>"
                    "<li>find clear, practical summaries "
                    "of autism research</li>"

                    "<li>access tools, guidance and resources "
                    "that help you put research into practice</li>"

                    "<li>understand what research tells us, "
                    "where there is uncertainty, and what "
                    "we still need to learn</li>"

                    "<li>see how research can inform everyday "
                    "decisions, services, practice and policy</li>"

                    "<li>learn about neurodiversity-affirming "
                    "and culturally safe approaches to "
                    "autism research</li>"
                    "</ul>"
                ),
            },
        ),

        (
            "section",
            {
                "heading": "Have a say in what we do",
                "body": (
                    "<p>The Hub is built on partnership, and there "
                    "are opportunities for you to be part of its "
                    "work. Autistic people, families and community "
                    "organisations are involved throughout the "
                    "Hub's activities, not simply consulted at "
                    "the end. Depending on your interests and "
                    "experience, you may be able to:</p>"

                    "<ul>"
                    "<li>help identify the questions and topics "
                    "that need more attention</li>"

                    "<li>contribute to how research is designed</li>"

                    "<li>help us understand what research findings "
                    "mean in the context of people's lives</li>"

                    "<li>shape how research is communicated "
                    "and put into practice</li>"
                    "</ul>"

                    "<p>By working together, we can focus on the "
                    "knowledge that matters to the autism community "
                    "and make it more useful in the places where "
                    "it can make a difference. You can let us know "
                    "what you are interested in by completing "
                    "our community connections form in the "
                    "Stay in Touch page.</p>"
                ),
            },
        ),

        (
            "team_section",
            {
                "heading": "Who's working at the Hub",

                "intro": (
                    "<p>The Australian Autism Knowledge Hub includes "
                    "Autistic, neurodivergent (but not Autistic) "
                    "and non-autistic people. The Hub is hosted "
                    "by the Olga Tennison Autism Research Centre "
                    "(OTARC) at La Trobe University.</p>"

                    "<p><b>The Hub is led by:</b></p>"
                ),

                "members": [
                    {
                        "image": None,
                        "name": "Professor Dawn Adams",
                        "role": "Hub Director",
                        "bio": (
                            "<p>An internationally recognised "
                            "autism researcher.</p>"
                        ),
                    },
                    {
                        "image": None,
                        "name": "Associate Professor Josie Barbaro",
                        "role": (
                            "Deputy Director, "
                            "Knowledge Translation"
                        ),
                        "bio": (
                            "<p>An Autistic academic with expertise "
                            "in making research knowledge accessible "
                            "and useful to the people who need it.</p>"
                        ),
                    },
                    {
                        "image": None,
                        "name": "Dr Melanie Heyworth",
                        "role": (
                            "Deputy Director, "
                            "Community and Co-Design"
                        ),
                        "bio": (
                            "<p>An Autistic researcher and leader "
                            "in community co-design, with expertise "
                            "in bringing Autistic people and "
                            "communities into genuine partnership "
                            "with research and practice.</p>"
                        ),
                    },
                ],

                "partnership": (
                    "<p>The Hub will be working in partnership "
                    "with La Trobe University's Gabra Biik, "
                    "Wurruwila Wutja Centre to embed First Nations "
                    "leadership and culturally safe practices "
                    "in our work, including our approach to "
                    "Indigenous data sovereignty.</p>"
                ),

                "more_team_label": (
                    "Meet the rest of the Hub team"
                ),

                "more_team_url": "",

                "funding": (
                    "<p>The Australian Autism Knowledge Hub is "
                    "funded by the Australian Government "
                    "Department of Health, Disability and Ageing "
                    "for three years, from July 2026 "
                    "to June 2029.</p>"
                ),
            },
        ),
    ]

class GenericPage(Page):
    """A flexible information page for top-level website content."""

    intro = RichTextField(
    blank=True,
    features=["bold", "italic", "link"],

    default=(
        "<p>We turn autism research into clear, trustworthy "
        "information that autistic people, families, educators, "
        "and health professionals can actually understand "
        "and use.</p>"
    ),

    help_text="Short introduction shown below the page title.",
    )

    body = StreamField(
    [
        ("section", ContentSectionBlock()),
        ("team_section", TeamSectionBlock()),
    ],
    blank=True,
    use_json_field=True,
    default=default_about_body,
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
