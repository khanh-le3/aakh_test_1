from datetime import date
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.admin.panels import FieldPanel
from wagtail.admin.rich_text import get_rich_text_editor_widget
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Page, PageViewRestriction, Site
from wagtail.search.backends import get_search_backend
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from .blocks import RESOURCE_RICH_TEXT_FEATURES, ResourceContentBlock
from .models import (
    KnowledgeLibraryPage,
    ResourceIndexPage,
    ResourcePage,
    TopicIndexPage,
    TopicPage,
)
from .topics import TOPIC_KEYS


def resource_body(*blocks):
    return ResourcePage._meta.get_field("body").stream_block.to_python(
        [{"type": block_type, "value": value} for block_type, value in blocks]
    )


class ResourcePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.library = KnowledgeLibraryPage.objects.get()
        cls.resource_index = ResourceIndexPage.objects.get()
        cls.topics = list(TopicPage.objects.order_by("path"))
        cls.resource = cls.resource_index.add_child(
            instance=ResourcePage(
                title="Making information easier to use",
                slug="making-information-easier",
                full_summary="Practical ways to present information clearly.",
                short_summary="Ideas for clearer information.",
                resource_type="snapshot",
                primary_topic=cls.topics[0],
                publication_date=date(2026, 1, 12),
                review_date=date(2026, 8, 23),
                citation='<p><a href="https://example.org/evidence">Read the evidence</a></p>',
                reading_time=3,
                body=resource_body(
                    ("heading_2", "Start with the reader"),
                    ("paragraph", "<p>Use familiar words and clear examples.</p>"),
                ),
            )
        )
        cls.resource.save_revision().publish()

    def setUp(self):
        Site.clear_site_root_paths_cache()
        self.addCleanup(Site.clear_site_root_paths_cache)

    def page_form_data(self):
        data = nested_form_data(
            {
                "title": self.resource.title,
                "slug": self.resource.slug,
                "full_summary": self.resource.full_summary,
                "short_summary": self.resource.short_summary,
                "resource_type": self.resource.resource_type,
                "primary_topic": str(self.topics[0].pk),
                "publication_date": "2026-01-12",
                "review_date": "2026-08-23",
                "citation": rich_text(
                    self.resource.citation, features=["bold", "italic", "link"]
                ),
                "keywords": "internal editorial phrase",
                "body": streamfield(
                    [
                        ("heading_2", "Start with the reader"),
                        (
                            "paragraph",
                            rich_text("<p>Use familiar words and clear examples.</p>"),
                        ),
                    ]
                ),
            }
        )
        data["secondary_topics"] = []
        return data

    def page_form(self, data):
        form_class = ResourcePage.get_edit_handler().get_form_class()
        return form_class(
            data=data, instance=self.resource, parent_page=self.resource_index
        )

    def test_seeded_tree_has_twelve_real_topic_destinations_and_flat_resources(self):
        self.assertEqual(set(TopicPage.objects.values_list("topic_key", flat=True)), TOPIC_KEYS)
        topic_index = TopicIndexPage.objects.get()
        self.assertEqual(topic_index.get_parent().pk, self.library.pk)
        self.assertEqual(self.resource_index.get_parent().pk, self.library.pk)
        self.assertEqual(self.resource.url, "/knowledge-library/resources/making-information-easier/")
        self.assertTrue(ResourcePage.can_exist_under(self.resource_index))
        self.assertFalse(ResourcePage.can_exist_under(self.topics[0]))
        self.assertEqual(Page.find_problems(), ([], [], [], [], []))
        for card in self.library.topic_cards.all():
            with self.subTest(topic=card.topic_key):
                topic = TopicPage.objects.get(topic_key=card.topic_key)
                self.assertEqual(card.url, topic.url)
                self.assertEqual(self.client.get(card.url).status_code, 200)
        self.assertRedirects(
            self.client.get(topic_index.url), self.library.url, fetch_redirect_response=False
        )

    def test_admin_form_accepts_boundary_lengths_and_editable_metadata(self):
        data = self.page_form_data()
        data.update(
            title=" ".join(["word"] * 30),
            full_summary="\n".join(["word"] * 150),
            short_summary=" ".join(["word"] * 40),
            resource_type="guideline",
            secondary_topics=[str(topic.pk) for topic in self.topics[1:3]],
        )
        form = self.page_form(data)
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save(commit=False)
        self.assertEqual(updated.resource_type, "guideline")
        self.assertEqual(updated.publication_date, date(2026, 1, 12))
        self.assertEqual(updated.review_date, date(2026, 8, 23))
        self.assertEqual(set(updated.secondary_topics.all()), set(self.topics[1:3]))
        self.assertIn("https://example.org/evidence", updated.citation)

    def test_reading_time_uses_saved_wagtail_value_including_zero(self):
        for minutes in (0, 1, 7):
            with self.subTest(minutes=minutes):
                self.resource.reading_time = minutes
                self.resource.save_revision().publish()
                response = self.client.get(self.resource.url)
                self.assertContains(response, f"{minutes} minute read")
                response = self.client.get(self.library.url)
                self.assertContains(response, f"{minutes} minute{'s' if minutes != 1 else ''}</dd>")

    def test_missing_wagtail_metric_is_omitted_on_page_and_card(self):
        self.resource.reading_time = None
        self.resource.save_revision().publish()
        self.assertNotContains(self.client.get(self.resource.url), "minute read")
        self.assertNotContains(self.client.get(self.library.url), "<dt>Read time</dt>")

    def test_reading_time_stays_with_its_revision_until_published(self):
        self.resource.reading_time = 7
        revision = self.resource.save_revision()
        self.assertEqual(ResourcePage.objects.get(pk=self.resource.pk).reading_time, 3)
        self.assertEqual(revision.as_object().reading_time, 7)
        revision.publish()
        self.assertEqual(ResourcePage.objects.get(pk=self.resource.pk).reading_time, 7)

    def test_editor_captures_metric_and_does_not_reuse_an_old_value(self):
        form_class = ResourcePage.get_edit_handler().get_form_class()
        unbound = form_class(instance=self.resource, parent_page=self.resource_index)
        self.assertIsNone(unbound["reading_time"].value())
        self.assertTrue(unbound.fields["reading_time"].widget.is_hidden)
        self.assertIn("resource-metrics.js", str(unbound.media))
        for submitted, expected in (("7", 7), ("0", 0), ("", None)):
            data = self.page_form_data()
            data["reading_time"] = submitted
            form = self.page_form(data)
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.save(commit=False).reading_time, expected)
        data = self.page_form_data()
        form = self.page_form(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save(commit=False).reading_time)
        for invalid in ("-1", "1.5", "unknown"):
            data["reading_time"] = invalid
            form = self.page_form(data)
            self.assertFalse(form.is_valid())
            self.assertIn("reading_time", form.errors)

    def test_admin_form_rejects_overlong_or_missing_copy_with_field_errors(self):
        for field, limit in (("title", 30), ("full_summary", 150), ("short_summary", 40)):
            for value in (" ".join(["word"] * (limit + 1)), ""):
                with self.subTest(field=field, value_length=len(value)):
                    data = self.page_form_data()
                    data[field] = value
                    form = self.page_form(data)
                    self.assertFalse(form.is_valid())
                    self.assertIn(field, form.errors)

    def test_admin_form_requires_one_known_type_and_primary_topic(self):
        for field, value in (
            ("resource_type", "video"),
            ("resource_type", "snapshot,framework"),
            ("resource_type", ""),
            ("primary_topic", ""),
            ("primary_topic", str(self.library.pk)),
        ):
            with self.subTest(field=field, value=value):
                data = self.page_form_data()
                data[field] = value
                form = self.page_form(data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_admin_form_rejects_too_many_or_repeated_primary_topics_and_recovers(self):
        for selections in (self.topics[1:4], self.topics[:2]):
            with self.subTest(selections=[topic.topic_key for topic in selections]):
                data = self.page_form_data()
                data["secondary_topics"] = [str(topic.pk) for topic in selections]
                form = self.page_form(data)
                self.assertFalse(form.is_valid())
                self.assertIn("secondary_topics", form.errors)
                data["secondary_topics"] = [str(self.topics[1].pk)]
                corrected = self.page_form(data)
                self.assertTrue(corrected.is_valid(), corrected.errors)

    def test_admin_form_reports_review_date_before_publication(self):
        data = self.page_form_data()
        data["review_date"] = "2026-01-11"
        form = self.page_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("review_date", form.errors)
        data["review_date"] = "2026-01-12"
        form = self.page_form(data)
        self.assertTrue(form.is_valid(), form.errors)
        data["review_date"] = ""
        form = self.page_form(data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_reports_invalid_body_and_accepts_a_corrected_heading(self):
        data = self.page_form_data()
        data["body-0-type"] = "heading_4"
        form = self.page_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)
        panel = FieldPanel("body").bind_to_model(ResourcePage).get_bound_panel(
            instance=self.resource, form=form
        )
        self.assertIn("Start with a level 2 heading", panel.render_html())
        data["body-0-type"] = "heading_2"
        corrected = self.page_form(data)
        self.assertTrue(corrected.is_valid(), corrected.errors)
        data.update(nested_form_data({"body": streamfield([])}))
        empty = self.page_form(data)
        self.assertFalse(empty.is_valid())
        self.assertIn("body", empty.errors)

    def test_programmatic_revision_cannot_bypass_accessible_body_validation(self):
        revision_count = self.resource.revisions.count()
        for body in (
            resource_body(("heading_4", "A skipped heading level")),
            resource_body(("paragraph", '<p><a href="javascript:alert(1)">Unsafe</a></p>')),
            resource_body(),
        ):
            with self.subTest(body=str(body)):
                self.resource.body = body
                with self.assertRaises(ValidationError) as error:
                    self.resource.save_revision()
                self.assertIn("body", error.exception.message_dict)
                self.assertEqual(self.resource.revisions.count(), revision_count)

    def test_draft_body_topics_and_keywords_are_isolated_until_publication(self):
        self.resource.keywords.add("original internal keyword")
        self.resource.secondary_topics.add(self.topics[1])
        self.resource.save_revision().publish()
        self.resource.refresh_from_db()
        self.resource.body = resource_body(
            ("heading_2", "Draft resource heading"),
            ("paragraph", "<p>Draft body awaiting approval.</p>"),
        )
        self.resource.full_summary = "Draft summary awaiting approval."
        self.resource.secondary_topics.set([self.topics[2]])
        self.resource.keywords.set(["private draft keyword"])
        revision = self.resource.save_revision()

        published = ResourcePage.objects.get(pk=self.resource.pk)
        self.assertEqual(published.full_summary, "Practical ways to present information clearly.")
        self.assertEqual(list(published.secondary_topics.all()), [self.topics[1]])
        self.assertEqual(list(published.keywords.names()), ["original internal keyword"])
        response = self.client.get(published.url)
        self.assertContains(response, "Start with the reader")
        self.assertNotContains(response, "Draft resource heading")
        self.assertNotContains(response, "original internal keyword")
        draft = revision.as_object()
        self.assertEqual(list(draft.keywords.names()), ["private draft keyword"])
        self.assertEqual(list(draft.secondary_topics.all()), [self.topics[2]])

        revision.publish()
        response = self.client.get(published.url)
        self.assertContains(response, "Draft resource heading")
        self.assertContains(response, "Draft summary awaiting approval.")
        self.assertNotContains(response, "private draft keyword")

    @override_settings(DEBUG=False)
    def test_banner_breadcrumbs_and_metadata_are_server_rendered(self):
        self.resource.secondary_topics.add(self.topics[1], self.topics[2])
        self.resource.save_revision().publish()
        response = self.client.get(self.resource.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "knowledge_library/resource_page.html")
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual([heading.get_text(strip=True) for heading in soup.select("h1")], [self.resource.title])
        breadcrumb = soup.find("nav", attrs={"aria-label": "Breadcrumb"})
        self.assertIsNotNone(breadcrumb)
        self.assertEqual(
            [item.get_text(" ", strip=True) for item in breadcrumb.select("li")],
            ["Home", "Knowledge library", self.resource.title],
        )
        self.assertEqual(
            [link["href"] for link in breadcrumb.select("a[href]")][:2],
            ["/", self.library.url],
        )
        self.assertNotIn(self.resource_index.url, [link["href"] for link in breadcrumb.select("a[href]")])
        self.assertIsNotNone(breadcrumb.select_one('[aria-current="page"]'))
        self.assertContains(response, self.resource.full_summary)
        self.assertContains(response, "Snapshot")
        self.assertContains(response, "January 2026")
        self.assertContains(response, "August 2026")
        self.assertIsNotNone(soup.find("a", href="https://example.org/evidence"))
        for topic in self.topics[:3]:
            self.assertIsNotNone(soup.find("a", href=topic.url))

    def test_resource_and_topic_listings_exclude_drafts_and_restricted_pages(self):
        self.resource.secondary_topics.add(self.topics[1])
        self.resource.save_revision().publish()
        for topic in self.topics[:2]:
            self.assertContains(self.client.get(topic.url), self.resource.url)
        self.assertContains(self.client.get(self.resource_index.url), self.resource.short_summary)
        self.assertNotContains(self.client.get(self.topics[2].url), self.resource.url)
        self.resource.live = False
        self.resource.save(update_fields=["live"])
        for url in (self.resource_index.url, self.topics[0].url, self.topics[1].url):
            self.assertNotContains(self.client.get(url), self.resource.url)
        self.assertEqual(self.client.get(self.resource.url).status_code, 404)

        self.resource.live = True
        self.resource.save(update_fields=["live"])
        PageViewRestriction.objects.create(
            page=self.resource, restriction_type=PageViewRestriction.LOGIN
        )
        for url in (self.resource_index.url, self.topics[0].url, self.topics[1].url):
            self.assertNotContains(self.client.get(url), self.resource.url)

    def test_topic_listing_excludes_resources_with_a_restricted_ancestor(self):
        PageViewRestriction.objects.create(
            page=self.resource_index, restriction_type=PageViewRestriction.LOGIN
        )
        self.assertNotContains(self.client.get(self.topics[0].url), self.resource.url)

    def test_site_search_excludes_restricted_resources(self):
        get_search_backend().add(self.resource)
        response = self.client.get(reverse("search"), {"query": "Making"})
        self.assertContains(response, self.resource.url)
        PageViewRestriction.objects.create(
            page=self.resource, restriction_type=PageViewRestriction.LOGIN
        )
        response = self.client.get(reverse("search"), {"query": "Making"})
        self.assertNotContains(response, self.resource.url)
        self.assertNotContains(response, self.resource.title)

    def test_site_search_never_links_the_redirect_only_topic_index(self):
        topic_index = TopicIndexPage.objects.get()
        get_search_backend().add(topic_index)
        # Prove the fixture is indexed so an empty result cannot mask a regression.
        self.assertEqual(
            list(Page.objects.filter(pk=topic_index.pk).search("Topics")),
            [topic_index.page_ptr],
        )
        response = self.client.get(reverse("search"), {"query": "Topics"})
        self.assertNotContains(response, f'href="{topic_index.url}"')

    def test_toc_links_resolve_to_unique_headings_without_javascript(self):
        headings = [
            ("heading_2", "Getting started"),
            ("heading_3", "More detail"),
            ("heading_4", "An example"),
            ("heading_3", "An example"),
            ("heading_2", "Getting started"),
            ("heading_2", "Getting started 2"),
            ("heading_2", "理解自闭症"),
            ("heading_2", "理解自闭症"),
            ("heading_2", "???"),
        ]
        self.resource.body = resource_body(*headings)
        self.resource.save_revision().publish()
        response = self.client.get(self.resource.url)
        soup = BeautifulSoup(response.content, "html.parser")
        content_headings = soup.select(".resource-content h2, .resource-content h3, .resource-content h4")
        self.assertEqual(
            [(heading.name, heading.get_text(strip=True)) for heading in content_headings],
            [(f"h{block_type[-1]}", text) for block_type, text in headings],
        )
        ids = [heading["id"] for heading in content_headings]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertTrue(all(ids))
        links = soup.select(".resource-toc a[href]")
        toc_headings = [heading for heading in content_headings if heading.name in {"h2", "h3"}]
        self.assertEqual([link["href"] for link in links], [f"#{heading['id']}" for heading in toc_headings])
        self.assertEqual(
            [link.get_text(strip=True) for link in links],
            [text for block_type, text in headings if block_type in {"heading_2", "heading_3"}],
        )
        self.assertEqual(
            [link.get_text(strip=True) for link in links[0].parent.select(":scope > ul > li > a")],
            ["More detail", "An example"],
        )
        self.assertEqual(links[0].parent.parent, links[3].parent.parent)
        self.assertEqual(len(soup.select("h1")), 1)
        self.assertIsNotNone(soup.select_one(".resource-toc ol ol, .resource-toc ul ul"))

    def test_resource_without_headings_does_not_render_empty_navigation(self):
        self.resource.body = resource_body(("paragraph", "<p>A short resource without sections.</p>"))
        self.resource.review_date = None
        self.resource.save_revision().publish()
        response = self.client.get(self.resource.url)
        self.assertContains(response, "A short resource without sections.")
        self.assertNotContains(response, "On this page")
        self.assertNotContains(response, "Reviewed:")

    def test_wagtail_editor_exposes_resource_fields_and_registered_formatting(self):
        editor = get_user_model().objects.create_user(
            username="resource-editor", is_staff=True, is_superuser=True
        )
        self.client.force_login(editor)
        response = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.resource.pk]))
        self.assertEqual(response.status_code, 200)
        for field in (
            "full_summary", "short_summary", "resource_type", "primary_topic",
            "secondary_topics", "keywords", "publication_date", "review_date", "citation",
        ):
            self.assertContains(response, f'name="{field}"')


class ResourceContentTests(TestCase):
    def setUp(self):
        self.blocks = ResourceContentBlock()

    def clean_block(self, name, value):
        block = self.blocks.child_blocks[name]
        return block.clean(block.to_python(value))

    def render_block(self, name, value):
        block = self.blocks.child_blocks[name]
        return BeautifulSoup(block.render(self.clean_block(name, value)), "html.parser")

    def test_heading_validation_reports_the_block_and_allows_corrected_structure(self):
        for headings, invalid_index in (
            ([("heading_3", "Skipped section")], 0),
            ([("heading_2", "Section"), ("heading_4", "Skipped subheading")], 1),
        ):
            with self.subTest(headings=headings):
                with self.assertRaises(StreamBlockValidationError) as error:
                    self.blocks.clean(resource_body(*headings))
                self.assertIn(invalid_index, error.exception.block_errors)
        cleaned = self.blocks.clean(resource_body(
            ("heading_2", "Section"), ("heading_3", "Subsection"),
            ("heading_4", "Detail"), ("heading_2", "Next section"),
        ))
        self.assertEqual(len(cleaned), 4)

    def test_rich_text_rejects_hidden_headings_unsafe_links_and_arbitrary_styles(self):
        for source in (
            "<h2>A heading outside the navigation</h2>",
            '<p><a href="javascript:alert(1)">Unsafe link</a></p>',
            '<p><span style="color: #eeeeee">Unreadable text</span></p>',
            "<p> &nbsp; </p>",
        ):
            with self.subTest(source=source):
                with self.assertRaises(ValidationError):
                    self.clean_block("paragraph", source)

    def test_rich_text_editor_preserves_accessible_formatting_and_lists(self):
        source = (
            '<p><b>Bold</b> <i>Italic</i> <u>Underline</u> '
            '<span class="resource-text resource-text--primary">Primary</span> '
            '<span class="resource-text resource-text--secondary">Secondary</span> '
            '<a href="https://example.org/reference">Reference</a></p>'
            '<ul><li>First idea</li></ul><ol><li>First step</li></ol>'
        )
        widget = get_rich_text_editor_widget(features=RESOURCE_RICH_TEXT_FEATURES)
        saved_html = widget.value_from_datadict(
            {"body": widget.format_value(source)}, {}, "body"
        )
        soup = self.render_block("paragraph", saved_html)
        for selector in (
            "b, strong", "i, em", "u", "span.resource-text--primary",
            "span.resource-text--secondary", "ul li", "ol li",
            'a[href="https://example.org/reference"]',
        ):
            self.assertIsNotNone(soup.select_one(selector), selector)

    def test_table_requires_caption_headers_and_matching_cells(self):
        table = {
            "caption": "Ways to make information clear",
            "headers": ["Format", "Example"],
            "rows": [["Words", "Use plain language"], ["Images", "Explain diagrams"]],
            "first_column_is_header": True,
        }
        for changes, error_field in (
            ({"caption": ""}, "caption"),
            ({"headers": ["Format", ""]}, "headers"),
            ({"rows": [["Words"]]}, "rows"),
            ({"rows": [["", "Use plain language"]]}, "rows"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(StructBlockValidationError) as error:
                    self.clean_block("table", {**table, **changes})
                self.assertIn(error_field, error.exception.block_errors)
        soup = self.render_block("table", table)
        self.assertEqual(soup.caption.get_text(strip=True), table["caption"])
        self.assertEqual([cell.get_text(strip=True) for cell in soup.select('th[scope="col"]')], table["headers"])
        self.assertEqual([cell.get_text(strip=True) for cell in soup.select('th[scope="row"]')], ["Words", "Images"])

    def test_image_requires_an_explicit_information_or_decoration_choice(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            image = get_image_model().objects.create(
                title="An editorial image title", file=get_test_image_file()
            )
            value = {"image": image.pk, "alt_text": "", "decorative": False, "caption": ""}
            with self.assertRaises(StructBlockValidationError) as error:
                self.clean_block("image", value)
            self.assertIn("alt_text", error.exception.block_errors)
            informative = self.render_block("image", {**value, "alt_text": "A reader follows a written checklist."})
            self.assertEqual(informative.img["alt"], "A reader follows a written checklist.")
            decorative = self.render_block("image", {**value, "decorative": True})
            self.assertEqual(decorative.img["alt"], "")
            with self.assertRaises(StructBlockValidationError):
                self.clean_block("image", {**value, "decorative": True, "alt_text": "Contradictory alternative."})

    def test_media_require_alternatives_and_render_manual_native_controls(self):
        for media_type in ("audio", "video"):
            value = {
                "title": "Information in everyday life",
                "url": f"https://example.org/recording.{ 'mp4' if media_type == 'video' else 'mp3' }",
                "transcript": "<p>The speaker explains how to ask for clear information.</p>",
            }
            required_fields = ["title", "url", "transcript"]
            if media_type == "video":
                value.update(
                    captions_url="https://example.org/captions.vtt",
                    visual_information_in_audio=True,
                )
                required_fields.extend(["captions_url", "visual_information_in_audio"])
            for field in required_fields:
                with self.subTest(media_type=media_type, field=field):
                    missing_value = False if field == "visual_information_in_audio" else ""
                    with self.assertRaises(StructBlockValidationError) as error:
                        self.clean_block(media_type, {**value, field: missing_value})
                    self.assertIn(field, error.exception.block_errors)
            with self.assertRaises(StructBlockValidationError):
                self.clean_block(media_type, {**value, "url": "ftp://example.org/recording.mp3"})
            soup = self.render_block(media_type, value)
            player = soup.find(media_type)
            self.assertIsNotNone(player)
            self.assertIn("controls", player.attrs)
            self.assertNotIn("autoplay", player.attrs)
            self.assertIn("The speaker explains how to ask for clear information.", soup.get_text())
            if media_type == "video":
                track = player.find("track", kind="captions")
                self.assertIsNotNone(track)
                self.assertEqual(track["src"], value["captions_url"])
                self.assertEqual(track["srclang"], "en")
