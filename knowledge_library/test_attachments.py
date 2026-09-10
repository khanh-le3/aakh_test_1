"""Resource attachments use standard Wagtail documents and page revisions."""

from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader
from wagtail.blocks import StreamBlockValidationError
from wagtail.documents import get_document_model
from wagtail.models import Collection, CollectionViewRestriction, Site

from .blocks import ResourceContentBlock
from .models import ResourceIndexPage, ResourcePage, TopicPage
from .resource_pdf import resource_pdf_html


def attachment(document, **kwargs):
    return {"document": document.pk if document else None, "title": "", "description": "", **kwargs}


def body(files):
    return ResourceContentBlock().to_python([
        {"type": "heading_2", "value": "Supporting files"},
        {"type": "attachments", "value": {"files": files}},
    ])


class ResourceAttachmentsTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        Site.clear_site_root_paths_cache()
        self.addCleanup(Site.clear_site_root_paths_cache)
        Document = get_document_model()
        self.pdf = Document.objects.create(
            title="Plain language guide",
            file=SimpleUploadedFile("guide.pdf", b"%PDF-1.4\nattachment payload\n%%EOF", "application/pdf"),
        )
        self.docx = Document.objects.create(
            title="Planning worksheet",
            file=SimpleUploadedFile("worksheet.docx", b"editable worksheet payload"),
        )
        self.resource = ResourceIndexPage.objects.get().add_child(instance=ResourcePage(
            title="Resource with supporting files", slug="resource-with-files",
            full_summary="Choose the files that are useful to you.", short_summary="Supporting files.",
            resource_type="framework", publication_date=date(2026, 9, 1),
            primary_topic=TopicPage.objects.order_by("path").first(),
            body=body([
                attachment(self.pdf, description="Read an introduction to the framework."),
                attachment(self.docx, title="Make your own plan"),
            ]),
        ))
        self.resource.save_revision().publish()

    def test_rendered_downloads_have_titles_types_sizes_and_decorative_icons(self):
        response = self.client.get(self.resource.url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        links = soup.select(".resource-attachments__link")
        self.assertEqual([link["href"] for link in links], [self.pdf.url, self.docx.url])
        self.assertEqual([link.select_one(".resource-attachments__title").text for link in links],
                         ["Plain language guide", "Make your own plan"])
        for link, extension in zip(links, ["PDF", "DOCX"]):
            self.assertIn(f"File type: {extension} · Size: ", link.select_one(".resource-attachments__meta").text)
            self.assertIn("bytes", link.select_one(".resource-attachments__meta").text)
            self.assertEqual(link["target"], "_self")
            self.assertIn("download", link.attrs)
            self.assertEqual(link.svg["aria-hidden"], "true")
            self.assertEqual(link.svg["focusable"], "false")
        self.assertContains(response, "Read an introduction to the framework.")
        self.assertIsNotNone(soup.select_one('.resource-toc__link[href="#resource-section-supporting-files"]'))
        self.assertIsNotNone(soup.select_one(".resource-sidebar__download"))

    def test_editor_has_attachments_and_document_chooser_controls(self):
        user = get_user_model().objects.create_user(username="attachment-editor", is_staff=True, is_superuser=True)
        self.client.force_login(user)
        response = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.resource.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attachments")
        self.assertContains(response, "Choose a document")
        self.assertContains(response, "Optional download title")

    def test_files_are_required_and_blank_titles_fall_back_to_document_title(self):
        for files in ([], [attachment(None)]):
            with self.subTest(files=files), self.assertRaises(StreamBlockValidationError):
                ResourceContentBlock().clean(body(files))
        value = ResourceContentBlock().clean(body([attachment(self.pdf, title="  ")]))
        self.assertIn(self.pdf.title, str(value))

    def test_draft_edits_and_reordering_only_appear_after_publication(self):
        self.resource.body = body([attachment(self.docx, title="New approved title"), attachment(self.pdf)])
        revision = self.resource.save_revision()
        response = self.client.get(self.resource.url)
        self.assertContains(response, "Make your own plan")
        self.assertNotContains(response, "New approved title")
        revision.publish()
        soup = BeautifulSoup(self.client.get(self.resource.url).content, "html.parser")
        self.assertEqual([link["href"] for link in soup.select(".resource-attachments__link")],
                         [self.docx.url, self.pdf.url])
        self.assertIn("New approved title", soup.get_text())

    def test_download_streams_file_and_honours_collection_access_restrictions(self):
        response = self.client.get(self.pdf.url)
        self.assertEqual(response.status_code, 200)
        # Wagtail can serve PDFs inline; the same-origin download attribute
        # on the resource link requests a browser download for these too.
        self.assertIn("guide.pdf", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4\nattachment payload\n%%EOF")
        collection = Collection.get_first_root_node().add_child(name="Restricted downloads")
        self.pdf.collection = collection
        self.pdf.save()
        CollectionViewRestriction.objects.create(collection=collection, restriction_type=CollectionViewRestriction.LOGIN)
        self.assertEqual(self.client.get(self.pdf.url).status_code, 302)
        soup = BeautifulSoup(self.client.get(self.resource.url).content, "html.parser")
        restricted_link = soup.select_one(".resource-attachments__link")
        self.assertEqual(restricted_link["href"], self.pdf.url)
        self.assertNotIn("download", restricted_link.attrs)

    def test_deleted_documents_do_not_leave_empty_or_broken_download_links(self):
        self.pdf.delete()
        self.docx.delete()
        response = self.client.get(self.resource.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="resource-attachments"')

    def test_attachment_titles_and_descriptions_are_escaped(self):
        self.resource.body = body([attachment(self.pdf, title='<script>alert("title")</script>',
                                             description='<img src=x onerror="alert(1)">')])
        markup = str(self.resource.body)
        self.assertNotIn("<script>", markup)
        self.assertNotIn("<img", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_pdf_keeps_download_links_and_metadata_without_embedding_the_files(self):
        request = RequestFactory().get(self.resource.url)
        markup = resource_pdf_html(self.resource, request)
        self.assertNotIn("<svg", markup)
        response = self.client.get(f"{self.resource.url}download/")
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.content))
        text = " ".join(page.extract_text() for page in reader.pages)
        self.assertIn("Plain language guide", text)
        self.assertIn("Make your own plan", text)
        self.assertIn("DOCX", text)
        self.assertNotIn("attachment payload", text)
        urls = {
            urlsplit(annotation.get_object().get("/A", {}).get("/URI", "")).path
            for page in reader.pages for annotation in page.get("/Annots", [])
        }
        self.assertIn(self.pdf.url, urls)
        self.assertIn(self.docx.url, urls)
