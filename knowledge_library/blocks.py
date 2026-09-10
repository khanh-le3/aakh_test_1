"""Structured, accessible content blocks for knowledge resources."""

from html import unescape
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.html import strip_tags
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock


RESOURCE_RICH_TEXT_FEATURES = [
    "bold", "italic", "underline", "ol", "ul", "link", "document-link",
    "resource-primary", "resource-secondary",
]
TRANSCRIPT_FEATURES = ["bold", "italic", "ol", "ul", "link"]
HEADING_LEVELS = {"heading_2": 2, "heading_3": 3, "heading_4": 4}


class _ResourceMarkupValidator(HTMLParser):
    """Reject markup that would bypass the structured heading/colour editor."""

    allowed_tags = {"p", "br", "strong", "b", "em", "i", "u", "ol", "ul", "li", "a", "span"}
    colour_classes = {
        "resource-text resource-text--primary",
        "resource-text resource-text--secondary",
    }

    def handle_starttag(self, tag, attrs):
        if tag not in self.allowed_tags:
            raise ValidationError(
                "Use the heading, quote, table and media blocks for structured content."
            )
        for name, value in attrs:
            # Wagtail stores Draftail's stable block keys on paragraphs/list items.
            if name == "data-block-key" and tag in {"p", "li", "ul", "ol"}:
                continue
            if tag == "span" and name == "class" and value in self.colour_classes:
                continue
            if tag == "a" and name in {"href", "linktype", "id"}:
                if name == "href" and value and ":" in value.split("/")[0]:
                    scheme = value.partition(":")[0].lower()
                    if scheme not in {"http", "https", "mailto", "tel"}:
                        raise ValidationError("Use a web, email or telephone link.")
                continue
            raise ValidationError("Use the editor's formatting controls; custom HTML styles are not supported.")

    handle_startendtag = handle_starttag


class ResourceRichTextBlock(blocks.RichTextBlock):
    def clean(self, value):
        result = super().clean(value)
        source = result.source if hasattr(result, "source") else str(result)
        _ResourceMarkupValidator().feed(source)
        if self.required and not unescape(strip_tags(source)).strip():
            raise ValidationError("Enter some text.")
        return result


class ResourceImageBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    size = blocks.ChoiceBlock(
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("full", "Full body width"),
        ],
        default="full",
        label="Image size",
        help_text="Choose the display size. Images shrink to fit smaller screens. Use full body width for detailed diagrams or text that needs more space.",
    )
    alt_text = blocks.CharBlock(
        required=False, max_length=300,
        help_text="Describe the information the image conveys. For a complex diagram, also explain it in the surrounding text.",
    )
    decorative = blocks.BooleanBlock(
        required=False,
        help_text="Select only when the image adds no information. Leave alternative text empty for decorative images.",
    )
    caption = blocks.TextBlock(required=False)

    def clean(self, value):
        result = super().clean(value)
        if not result["decorative"] and not result["alt_text"].strip():
            raise blocks.StructBlockValidationError(block_errors={
                "alt_text": ValidationError("Describe this image, or mark it as decorative.")
            })
        if result["decorative"] and result["alt_text"].strip():
            raise blocks.StructBlockValidationError(block_errors={
                "alt_text": ValidationError("Remove alternative text for a decorative image.")
            })
        return result

    class Meta:
        template = "knowledge_library/blocks/resource_image.html"
        icon = "image"
        label = "Image"


class ResourceQuoteBlock(blocks.StructBlock):
    text = blocks.TextBlock()
    attribution = blocks.CharBlock(required=False, max_length=250)

    class Meta:
        template = "knowledge_library/blocks/resource_quote.html"
        icon = "openquote"
        label = "Quote"


class ResourceTableBlock(blocks.StructBlock):
    caption = blocks.CharBlock(max_length=250, help_text="Name the table and explain what it shows.")
    headers = blocks.ListBlock(blocks.CharBlock(max_length=200), min_num=1, label="Column headings")
    rows = blocks.ListBlock(
        blocks.ListBlock(blocks.TextBlock(required=False), min_num=1, label="Cells"),
        min_num=1,
        help_text="Add one cell for each column heading, in the same order.",
    )
    first_column_is_header = blocks.BooleanBlock(
        required=False, help_text="Select when the first column names each row."
    )

    def clean(self, value):
        result = super().clean(value)
        row_errors = {}
        for index, row in enumerate(result["rows"]):
            if len(row) != len(result["headers"]):
                row_errors[index] = ValidationError("Include one cell for each column heading.")
            elif result["first_column_is_header"] and not row[0].strip():
                row_errors[index] = ValidationError("Enter a heading in the first cell of this row.")
        if row_errors:
            raise blocks.StructBlockValidationError(block_errors={
                "rows": blocks.ListBlockValidationError(block_errors=row_errors)
            })
        return result

    class Meta:
        template = "knowledge_library/blocks/resource_table.html"
        icon = "table"
        label = "Table"


class ResourceAttachmentBlock(blocks.StructBlock):
    document = DocumentChooserBlock(
        help_text="Choose or upload a file. Check that its content is accessible before publishing.",
    )
    title = blocks.CharBlock(
        required=False,
        max_length=250,
        help_text="Optional download title. Leave blank to use the document's title.",
    )
    description = blocks.TextBlock(
        required=False,
        help_text="Optional short description of the file and who it is for.",
    )

    class Meta:
        icon = "doc-full"
        label = "Attachment"
        label_format = "{title}"


class ResourceAttachmentsBlock(blocks.StructBlock):
    files = blocks.ListBlock(
        ResourceAttachmentBlock(),
        min_num=1,
        label="Files",
        help_text="Add files in the order readers should see them. Use a separate section heading above this block to name the group.",
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        # A deleted document can remain in an older revision. Do not render
        # an empty download link if that revision is viewed or restored.
        context["attachments"] = [
            {
                "document": item["document"],
                "title": item.get("title", "").strip() or item["document"].title,
                "description": item.get("description", ""),
                "file_size": item["document"].get_file_size(),
                # Restricted documents must navigate through Wagtail's
                # access form, rather than downloading that form as HTML.
                "download_directly": not item["document"].collection.get_view_restrictions().exists(),
            }
            for item in value["files"]
            if item["document"] and item["document"].file
        ]
        return context

    class Meta:
        template = "knowledge_library/blocks/resource_attachments.html"
        icon = "doc-full"
        label = "Attachments"


class ResourceAudioBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200, help_text="A descriptive name for the recording.")
    url = blocks.URLBlock(
        validators=[URLValidator(schemes=["http", "https"])],
        help_text="Direct web address of an audio file, such as MP3. The host must permit playback on this site.",
    )
    transcript = ResourceRichTextBlock(
        features=TRANSCRIPT_FEATURES,
        help_text="Include all speech and meaningful sounds. The transcript is displayed below the player.",
    )

    class Meta:
        template = "knowledge_library/blocks/resource_audio.html"
        icon = "media"
        label = "Audio"


class ResourceVideoBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200, help_text="A descriptive name for the video.")
    url = blocks.URLBlock(
        validators=[URLValidator(schemes=["http", "https"])],
        help_text="Direct web address of a video file, such as MP4. The host must permit cross-origin playback on this site.",
    )
    captions_url = blocks.URLBlock(
        validators=[URLValidator(schemes=["http", "https"])],
        help_text="WebVTT captions file in English, including speech and meaningful sounds. Its host must allow cross-origin access.",
    )
    transcript = ResourceRichTextBlock(
        features=TRANSCRIPT_FEATURES,
        help_text="Include all speech, meaningful sounds and descriptions of important visual information.",
    )
    visual_information_in_audio = blocks.BooleanBlock(
        required=True,
        label="Important visual information is described in the audio",
        help_text="Check the soundtrack describes essential visuals. If needed, use an audio-described version of the video.",
    )

    class Meta:
        template = "knowledge_library/blocks/resource_video.html"
        icon = "media"
        label = "Video"


class ResourceContentBlock(blocks.StreamBlock):
    heading_2 = blocks.CharBlock(max_length=160, label="Section heading (level 2)", icon="title")
    heading_3 = blocks.CharBlock(max_length=160, label="Subheading (level 3)", icon="title")
    heading_4 = blocks.CharBlock(max_length=160, label="Subheading (level 4)", icon="title")
    paragraph = ResourceRichTextBlock(
        features=RESOURCE_RICH_TEXT_FEATURES,
        template="knowledge_library/blocks/resource_text.html",
        help_text="Write paragraphs and lists here. Use separate heading blocks for sections. Colour must not be the only way you communicate meaning.",
    )
    quote = ResourceQuoteBlock()
    table = ResourceTableBlock()
    image = ResourceImageBlock()
    video = ResourceVideoBlock()
    audio = ResourceAudioBlock()
    attachments = ResourceAttachmentsBlock()

    def clean(self, value):
        result = super().clean(value)
        previous_level = 1
        errors = {}
        for index, block in enumerate(result):
            level = HEADING_LEVELS.get(block.block_type)
            if level is None:
                continue
            if level > previous_level + 1:
                errors[index] = ValidationError(
                    "Start with a level 2 heading and do not skip heading levels."
                )
            previous_level = level
        if errors:
            raise blocks.StreamBlockValidationError(block_errors=errors)
        return result
