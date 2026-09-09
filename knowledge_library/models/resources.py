"""Resource pages, their listing, and editorial validation."""

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from django.utils import timezone
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import TaggedItemBase
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.models import Page
from wagtail.search import index

from ..blocks import ResourceContentBlock
from ..resource_content import resource_content_context
from ..validators import MaxWordsValidator
from .shared import FixedLibraryPathMixin, library_context, resource_listing_context
from .topics import TopicPage


class ResourceIndexPage(FixedLibraryPathMixin, Page):
    """The flat listing and canonical parent for every resource."""

    is_creatable = False
    max_count = 1
    fixed_slug = "resources"
    parent_page_types = ["knowledge_library.KnowledgeLibraryPage"]
    subpage_types = ["knowledge_library.ResourcePage"]
    introduction = models.TextField(
        blank=True,
        default="Browse snapshots, frameworks, guidelines and reports.",
    )
    content_panels = FixedLibraryPathMixin.content_panels + [
        FieldPanel("introduction")
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        resources = ResourcePage.objects.child_of(self).live().public()
        context.update(resource_listing_context(self, request, resources))
        return context


def validate_resource_topics(primary_topic_id, secondary_topics):
    secondary_ids = [topic.pk for topic in secondary_topics]
    if len(secondary_ids) > 2:
        raise ValidationError("Choose no more than two secondary topics.")
    if primary_topic_id in secondary_ids:
        raise ValidationError("The primary topic cannot also be a secondary topic.")


class ResourcePageForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The editor supplies a fresh Wagtail metric for this revision.
        self.initial["reading_time"] = None

    class Media:
        js = ["knowledge_library/js/resource-metrics.js"]

    def clean(self):
        cleaned_data = super().clean()
        primary = cleaned_data.get("primary_topic")
        secondary = cleaned_data.get("secondary_topics")
        if secondary is not None:
            # Parental M2M values are normally assigned only when the form saves.
            # Stage them in memory so model validation checks the submitted draft.
            self.instance.secondary_topics.set(secondary)
            try:
                validate_resource_topics(primary.pk if primary else None, secondary)
            except ValidationError as error:
                self.add_error("secondary_topics", error)
        return cleaned_data


class ResourcePageKeyword(TaggedItemBase):
    content_object = ParentalKey(
        "knowledge_library.ResourcePage",
        on_delete=models.CASCADE,
        related_name="keyword_items",
    )


class ResourcePage(RoutablePageMixin, Page):
    """A moderated knowledge unit, independent of the topics assigned to it."""

    class ResourceType(models.TextChoices):
        SNAPSHOT = "snapshot", "Snapshot"
        FRAMEWORK = "framework", "Framework"
        GUIDELINE = "guideline", "Guideline"
        REPORT = "report", "Report"

    parent_page_types = ["knowledge_library.ResourceIndexPage"]
    subpage_types = []
    base_form_class = ResourcePageForm

    full_summary = models.TextField(
        validators=[MaxWordsValidator(150)],
        help_text="A plain-language introduction. Maximum 150 words.",
    )
    short_summary = models.TextField(
        validators=[MaxWordsValidator(40)],
        help_text="A short introduction for resource cards. Maximum 40 words.",
    )
    citation = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        help_text="Credit the source. Select text and use Link to add an external URL.",
    )
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    publication_date = models.DateField(default=timezone.localdate)
    review_date = models.DateField(
        blank=True,
        null=True,
        help_text="Leave blank until this resource has been reviewed.",
    )
    primary_topic = models.ForeignKey(
        TopicPage,
        on_delete=models.PROTECT,
        related_name="primary_resources",
    )
    secondary_topics = ParentalManyToManyField(
        TopicPage,
        blank=True,
        related_name="secondary_resources",
        help_text="Choose up to two topics, excluding the primary topic.",
    )
    keywords = ClusterTaggableManager(
        verbose_name="keywords",
        through=ResourcePageKeyword,
        blank=True,
        help_text="Internal editorial keywords. These are never shown to visitors.",
    )
    body = StreamField(ResourceContentBlock(), use_json_field=True)
    reading_time = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Reading time in minutes supplied by Wagtail's content metrics.",
    )

    content_panels = [
        TitleFieldPanel("title", help_text="Maximum 30 words."),
        FieldPanel("full_summary"),
        FieldPanel("citation"),
        MultiFieldPanel(
            [
                FieldPanel("short_summary"),
                FieldPanel("resource_type"),
                FieldPanel("publication_date"),
                FieldPanel("review_date"),
                FieldPanel("primary_topic", widget=forms.Select),
                FieldPanel("secondary_topics", widget=forms.CheckboxSelectMultiple),
                FieldPanel("keywords"),
            ],
            heading="Resource metadata",
        ),
        FieldPanel("body"),
        FieldPanel("reading_time", widget=forms.HiddenInput, classname="w-hidden"),
    ]
    search_fields = Page.search_fields + [
        index.SearchField("full_summary"),
        index.SearchField("short_summary"),
        index.SearchField("body"),
    ]

    def clean(self):
        super().clean()
        errors = {}
        try:
            # Model revisions also need the accessibility validation that the
            # StreamField admin widget normally performs on submitted blocks.
            self._meta.get_field("body").stream_block.clean(self.body)
        except ValidationError as error:
            errors["body"] = error
        try:
            MaxWordsValidator(30)(self.title)
        except ValidationError as error:
            errors["title"] = error
        try:
            validate_resource_topics(self.primary_topic_id, self.secondary_topics.all())
        except ValidationError as error:
            errors["secondary_topics"] = error
        if (
            self.publication_date
            and self.review_date
            and self.review_date < self.publication_date
        ):
            errors["review_date"] = "The review date cannot be before publication."
        if errors:
            raise ValidationError(errors)

    @property
    def topics(self):
        primary = [self.primary_topic] if self.primary_topic_id else []
        return primary + list(self.secondary_topics.all().order_by("title", "pk"))

    @path("download/", name="download_pdf")
    def download_pdf(self, request):
        # Wagtail routes the live page and checks inherited view restrictions
        # before this view runs, just as it does for the HTML resource.
        if request.method not in {"GET", "HEAD"}:
            return HttpResponseNotAllowed(["GET", "HEAD"])
        if Page.objects.ancestor_of(self).filter(depth__gt=1, live=False).exists():
            raise Http404
        from ..resource_pdf import render_resource_pdf

        response = HttpResponse(content_type="application/pdf")
        filename = f"{slugify(self.title, allow_unicode=True)[:120] or 'resource'}.pdf"
        response["Content-Disposition"] = content_disposition_header(True, filename)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        if request.method == "GET":
            response.content = render_resource_pdf(self, request)
        return response

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(library_context(self))
        context.update(resource_content_context(self.body))
        topics = self.topics
        public_topic_ids = set(
            TopicPage.objects.live()
            .public()
            .filter(pk__in=[topic.pk for topic in topics])
            .values_list("pk", flat=True)
        )
        for topic in topics:
            topic.resource_linkable = (
                topic.pk in public_topic_ids
                and not Page.objects.ancestor_of(topic)
                .filter(depth__gt=1, live=False)
                .exists()
            )
        context["topics"] = topics
        page_url = self.get_url(request)
        context["resource_pdf_url"] = (
            page_url + self.reverse_subpage("download_pdf") if page_url and self.live else None
        )
        return context
