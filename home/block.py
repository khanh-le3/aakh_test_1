from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


RICH_TEXT_FEATURES = [
    "bold",
    "italic",
    "link",
    "ul",
    "ol",
]


class ContentSectionBlock(blocks.StructBlock):
    heading = blocks.CharBlock(
        required=True,
        max_length=150,
    )

    body = blocks.RichTextBlock(
        required=True,
        features=RICH_TEXT_FEATURES,
    )

    class Meta:
        template = "home/blocks/content_section.html"
        label = "Content section"


class TeamMemberBlock(blocks.StructBlock):
    image = ImageChooserBlock(
        required=False,
    )

    name = blocks.CharBlock(
        required=True,
        max_length=120,
    )

    role = blocks.CharBlock(
        required=False,
        max_length=160,
    )

    bio = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link"],
    )

    class Meta:
        label = "Team member"


class TeamSectionBlock(blocks.StructBlock):
    heading = blocks.CharBlock(
        required=True,
        max_length=150,
        default="Who's working at the Hub",
    )

    intro = blocks.RichTextBlock(
        required=False,
        features=RICH_TEXT_FEATURES,
    )

    members = blocks.ListBlock(
        TeamMemberBlock(),
        min_num=1,
        max_num=12,
    )

    class Meta:
        template = "home/blocks/team_section.html"
        label = "Team section"