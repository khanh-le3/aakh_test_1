"""Exercise the download through Wagtail's publication and access controls."""

from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader
from weasyprint import HTML
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import PageViewRestriction, Site

from .models import KnowledgeLibraryPage, ResourceIndexPage, ResourcePage, TopicPage
from .resource_pdf import ResourcePDFFetcher, resource_pdf_html


def resource_body(*blocks):
    return ResourcePage._meta.get_field("body").stream_block.to_python(
        [{"type": block_type, "value": value} for block_type, value in blocks]
    )


def structure_elements(node):
    """Walk children only: PDF structure dictionaries also link to their parents."""
    if hasattr(node, "get_object"):
        node = node.get_object()
    if isinstance(node, list):
        for child in node:
            yield from structure_elements(child)
    elif isinstance(node, dict):
        if "/S" in node:
            yield node
        yield from structure_elements(node.get("/K"))


def outline_titles(outline):
    for item in outline:
        if isinstance(item, list):
            yield from outline_titles(item)
        else:
            yield item.title


class ResourcePDFTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.library = KnowledgeLibraryPage.objects.get()
        cls.resource_index = ResourceIndexPage.objects.get()
        cls.resource = cls.resource_index.add_child(
            instance=ResourcePage(
                title="Making information easier to use",
                slug="making-information-easier-pdf",
                full_summary="Practical ways to present information clearly.",
                short_summary="Ideas for clearer information.",
                resource_type="snapshot",
                primary_topic=TopicPage.objects.order_by("path").first(),
                publication_date=date(2026, 1, 12),
                review_date=date(2026, 8, 23),
                citation=(
                    '<p><a href="https://example.org/evidence">'
                    "Published research evidence</a></p>"
                ),
                body=resource_body(
                    ("heading_2", "Start with the reader"),
                    ("paragraph", "<p>Use familiar words and clear examples.</p>"),
                    ("heading_3", "Make the next step clear"),
                    ("paragraph", "<ol><li>Explain the choices.</li><li>Allow time.</li></ol>"),
                    ("heading_4", "An everyday example"),
                    ("paragraph", "<p>Offer written instructions for an appointment.</p>"),
                ),
            )
        )
        cls.resource.keywords.add("confidential editorial keyword")
        cls.resource.save_revision().publish()

    def setUp(self):
        Site.clear_site_root_paths_cache()
        self.addCleanup(Site.clear_site_root_paths_cache)
        self.download_url = f"{self.resource.url}download/"

    def assert_pdf(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertTrue(response.content.rstrip().endswith(b"%%EOF"))
        self.assertGreater(len(response.content), 1000)

    def test_download_returns_a_real_pdf_attachment(self):
        response = self.client.get(self.download_url)
        self.assert_pdf(response)
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="making-information-easier-to-use.pdf"',
        )

    def test_head_returns_download_headers_without_rendering(self):
        with patch("knowledge_library.resource_pdf.render_resource_pdf") as render_pdf:
            response = self.client.head(self.download_url)
        render_pdf.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="making-information-easier-to-use.pdf"',
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_post_is_rejected_without_rendering(self):
        with patch("knowledge_library.resource_pdf.render_resource_pdf") as render_pdf:
            response = self.client.post(self.download_url)
        render_pdf.assert_not_called()
        self.assertEqual(response.status_code, 405)
        self.assertEqual(set(response["Allow"].replace(" ", "").split(",")), {"GET", "HEAD"})

    @override_settings(CACHES={"default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "resource-pdf-publication-test",
    }})
    def test_repeated_download_is_cached_and_publication_regenerates_the_pdf(self):
        with patch("knowledge_library.resource_pdf.HTML", wraps=HTML) as renderer:
            first = self.client.get(self.download_url)
            repeated = self.client.get(self.download_url)
            self.assert_pdf(first)
            self.assertEqual(repeated.content, first.content)
            self.assertEqual(renderer.call_count, 1)

            self.resource.body = resource_body(
                ("heading_2", "Updated published advice"),
                ("paragraph", "<p>Ask the reader which format they prefer.</p>"),
            )
            self.resource.save_revision().publish()
            updated = self.client.get(self.download_url)
            self.assert_pdf(updated)
            self.assertEqual(renderer.call_count, 2)
        text = " ".join(page.extract_text() for page in PdfReader(BytesIO(updated.content)).pages)
        self.assertIn("Ask the reader which format they prefer.", text)
        self.assertNotIn("Use familiar words and clear examples.", text)

    def test_pdf_has_searchable_published_content_and_accessibility_structure(self):
        response = self.client.get(self.download_url)
        self.assert_pdf(response)
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
        for expected in (
            self.resource.title,
            self.resource.full_summary,
            "Use familiar words and clear examples.",
            "Explain the choices.",
            "Allow time.",
            "Offer written instructions for an appointment.",
            "Published research evidence",
            "Snapshot",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("confidential editorial keyword", text)
        self.assertEqual(reader.metadata.title, self.resource.title)
        root = reader.trailer["/Root"]
        self.assertEqual(root["/Lang"].lower(), "en-au")
        self.assertTrue(root["/MarkInfo"]["/Marked"])
        self.assertTrue(root["/ViewerPreferences"]["/DisplayDocTitle"])
        roles = [element["/S"] for element in structure_elements(root["/StructTreeRoot"])]
        self.assertEqual(roles.count("/H1"), 1)
        for role in ("/H2", "/H3", "/H4", "/L", "/LI", "/Link"):
            self.assertIn(role, roles)
        bookmarks = list(outline_titles(reader.outline))
        for heading in (
            self.resource.title,
            "Start with the reader",
            "Make the next step clear",
            "An everyday example",
        ):
            self.assertIn(heading, bookmarks)

    def test_unpublished_edits_do_not_leak_into_a_download(self):
        self.resource.title = "Unapproved resource title"
        self.resource.full_summary = "This summary has not been approved."
        self.resource.body = resource_body(
            ("heading_2", "Unapproved advice"),
            ("paragraph", "<p>This body has not been approved.</p>"),
        )
        self.resource.save_revision()
        response = self.client.get(self.download_url)
        self.assert_pdf(response)
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(page.extract_text() for page in reader.pages)
        self.assertEqual(reader.metadata.title, "Making information easier to use")
        self.assertIn("Use familiar words and clear examples.", text)
        self.assertNotIn("Unapproved", text)
        self.assertNotIn("has not been approved", text)

    def test_unpublished_resources_and_ancestors_cannot_be_downloaded(self):
        for page in (self.resource, self.resource_index, self.library):
            with self.subTest(page=page.title):
                page.live = False
                page.save(update_fields=["live"])
                self.assertEqual(self.client.get(self.download_url).status_code, 404)
                page.live = True
                page.save(update_fields=["live"])

    def test_login_restrictions_apply_to_resource_and_ancestor_downloads(self):
        user = get_user_model().objects.create_user(username="pdf-reader")
        for page in (self.resource, self.resource_index):
            with self.subTest(page=page.title):
                restriction = PageViewRestriction.objects.create(
                    page=page, restriction_type=PageViewRestriction.LOGIN
                )
                response = self.client.get(self.download_url)
                self.assertEqual(response.status_code, 302)
                self.assertNotEqual(response["Content-Type"], "application/pdf")
                self.client.force_login(user)
                self.assert_pdf(self.client.get(self.download_url))
                self.client.logout()
                restriction.delete()

    def test_password_restrictions_apply_to_resource_and_ancestor_downloads(self):
        for page in (self.resource, self.resource_index):
            with self.subTest(page=page.title):
                restriction = PageViewRestriction.objects.create(
                    page=page,
                    restriction_type=PageViewRestriction.PASSWORD,
                    password="reader-password",
                )
                response = self.client.get(self.download_url)
                self.assertEqual(response.status_code, 200)
                self.assertNotEqual(response["Content-Type"], "application/pdf")
                self.assertContains(response, 'type="password"')
                auth_url = reverse(
                    "wagtailcore_authenticate_with_password",
                    args=[restriction.pk, self.resource.pk],
                )
                self.assertRedirects(
                    self.client.post(
                        auth_url,
                        {"password": "reader-password", "return_url": self.download_url},
                    ),
                    self.download_url,
                    fetch_redirect_response=False,
                )
                self.assert_pdf(self.client.get(self.download_url))
                self.client.logout()
                restriction.delete()

    def test_pdf_preserves_image_alternatives_table_headers_and_media_transcripts(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            image = get_image_model().objects.create(
                title="Internal image title", file=get_test_image_file()
            )
            self.resource.body = resource_body(
                ("heading_2", "Examples and recordings"),
                ("image", {
                    "image": image.pk,
                    "size": "full",
                    "alt_text": "A reader follows a written checklist.",
                    "decorative": False,
                    "caption": "A written plan can help.",
                }),
                ("table", {
                    "caption": "Ways to make information clear",
                    "headers": ["Format", "Example"],
                    "rows": [["Words", "Use plain language"]],
                    "first_column_is_header": True,
                }),
                ("audio", {
                    "title": "Planning a conversation",
                    "url": "https://example.org/conversation.mp3",
                    "transcript": "<p>Ask which way of communicating works best.</p>",
                }),
                ("video", {
                    "title": "An appointment walkthrough",
                    "url": "https://example.org/appointment.mp4",
                    "captions_url": "https://example.org/appointment.vtt",
                    "visual_information_in_audio": True,
                    "transcript": "<p>The presenter shows a quiet waiting room.</p>",
                }),
            )
            self.resource.save_revision().publish()
            response = self.client.get(self.download_url)
        self.assert_pdf(response)
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
        for expected in (
            "A written plan can help.",
            "Ways to make information clear",
            "Format",
            "Example",
            "Use plain language",
            "Planning a conversation",
            "Ask which way of communicating works best.",
            "An appointment walkthrough",
            "The presenter shows a quiet waiting room.",
        ):
            self.assertIn(expected, text)
        elements = list(structure_elements(reader.trailer["/Root"]["/StructTreeRoot"]))
        self.assertIn(
            "A reader follows a written checklist.",
            [element.get("/Alt") for element in elements if element["/S"] == "/Figure"],
        )
        roles = [element["/S"] for element in elements]
        self.assertIn("/Table", roles)
        self.assertGreaterEqual(roles.count("/TH"), 3)
        self.assertIn("/TD", roles)
        urls = {
            annotation.get_object().get("/A", {}).get("/URI")
            for page in reader.pages
            for annotation in page.get("/Annots", [])
        }
        self.assertIn("https://example.org/conversation.mp3", urls)
        self.assertIn("https://example.org/appointment.mp4", urls)

    def test_decorative_images_do_not_create_unlabelled_pdf_figures(self):
        caption = "Readers can choose how they receive information."
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            image = get_image_model().objects.create(
                title="Decorative illustration", file=get_test_image_file()
            )
            self.resource.body = resource_body(
                ("heading_2", "Choose what works for you"),
                ("image", {
                    "image": image.pk,
                    "size": "full",
                    "alt_text": "",
                    "decorative": True,
                    "caption": caption,
                }),
            )
            self.resource.save_revision().publish()
            request = RequestFactory().get(self.resource.url)
            soup = BeautifulSoup(resource_pdf_html(self.resource, request), "html.parser")
            self.assertFalse(soup.select("img"))
            self.assertIn(caption, soup.get_text())
            response = self.client.get(self.download_url)
        self.assert_pdf(response)
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
        self.assertIn(caption, text)
        roles = [
            element["/S"]
            for element in structure_elements(reader.trailer["/Root"]["/StructTreeRoot"])
        ]
        self.assertNotIn("/Figure", roles)

    def test_wide_tables_preserve_every_label_and_value_as_readable_records(self):
        headers = ["Format", "Purpose", "Example", "Who chooses", "When"]
        rows = [
            ["Written", "Remember steps", "A checklist", "The reader", "Before a visit"],
            ["Spoken", "Discuss options", "A conversation", "The reader", "During a visit"],
        ]
        self.resource.body = resource_body(
            ("heading_2", "Choose a format"),
            ("table", {
                "caption": "Options for sharing information",
                "headers": headers,
                "rows": rows,
                "first_column_is_header": True,
            }),
        )
        request = RequestFactory().get(self.resource.url)
        soup = BeautifulSoup(resource_pdf_html(self.resource, request), "html.parser")
        records = soup.select_one(".resource-pdf__records")
        self.assertIsNotNone(records)
        self.assertIn("Options for sharing information", records.get_text())
        self.assertFalse(soup.select("table"))
        listings = records.select("dl")
        self.assertEqual(len(listings), len(rows))
        for listing, row in zip(listings, rows):
            self.assertEqual([term.get_text() for term in listing.select("dt")], headers)
            self.assertEqual([value.get_text() for value in listing.select("dd")], row)


class ResourcePDFFetcherTests(SimpleTestCase):
    def test_explicit_assets_are_returned_from_memory(self):
        url = "https://resource-pdf.invalid/static/approved.css"
        content = b"body { font-size: 12pt; }"
        fetcher = ResourcePDFFetcher({url: (content, "text/css")})
        with patch("urllib.request.OpenerDirector.open") as open_url:
            response = fetcher(url)
        self.addCleanup(response.close)
        open_url.assert_not_called()
        self.assertEqual(response.read(), content)
        self.assertEqual(response.content_type, "text/css")
        self.assertEqual(response.url, url)

    def test_unregistered_urls_cannot_trigger_file_or_network_access(self):
        approved = "https://resource-pdf.invalid/static/approved.css"
        fetcher = ResourcePDFFetcher({approved: (b"", "text/css")})
        with patch("urllib.request.OpenerDirector.open") as open_url:
            for url in (
                "file:///etc/passwd",
                "https://example.org/image.png",
                "http://127.0.0.1:8000/admin/",
                "http://169.254.169.254/latest/meta-data/",
                "/tmp/unregistered-image.png",
                "data:image/svg+xml,%3Csvg%3E%3C/svg%3E",
                approved + "?unregistered=1",
                "https://resource-pdf.invalid/static/../unregistered.png",
            ):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    fetcher(url)
        open_url.assert_not_called()
