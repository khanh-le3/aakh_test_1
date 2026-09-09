"""Published resources drive the library's recently added section."""

from datetime import date, timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone
from wagtail.models import PageViewRestriction, Site

from .models import KnowledgeLibraryPage, ResourceIndexPage, ResourcePage, TopicPage


class LibraryRecentResourcesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.library = KnowledgeLibraryPage.objects.get()
        cls.resource_index = ResourceIndexPage.objects.get()
        cls.topic = TopicPage.objects.order_by("path").first()
        cls.resources = []
        now = timezone.now()
        for number in range(21):
            resource = cls.resource_index.add_child(
                instance=ResourcePage(
                    title=f"Published library resource {number}",
                    slug=f"published-library-resource-{number}",
                    full_summary="A published resource summary.",
                    short_summary="A concise card introduction.",
                    resource_type="guideline",
                    reading_time=2,
                    primary_topic=cls.topic,
                    # Publication metadata deliberately runs in the opposite
                    # order: recently added uses the first CMS publication.
                    publication_date=date(2025, 1, 1) + timedelta(days=number),
                    first_published_at=now - timedelta(days=number),
                    live=True,
                    body=[
                        ("heading_2", "Useful information"),
                        ("paragraph", "<p>" + "Helpful " * 201 + "</p>"),
                    ],
                )
            )
            cls.resources.append(resource)

        cls.draft = cls.resource_index.add_child(
            instance=ResourcePage(
                title="Unpublished library resource",
                slug="unpublished-library-resource",
                full_summary="This draft must stay out of the library.",
                short_summary="An unpublished card introduction.",
                resource_type="report",
                primary_topic=cls.topic,
                live=False,
                body=[("paragraph", "<p>Draft content.</p>")],
            )
        )
        cls.private = cls.resource_index.add_child(
            instance=ResourcePage(
                title="Restricted library resource",
                slug="restricted-library-resource",
                full_summary="This restricted page must stay out of the library.",
                short_summary="A restricted card introduction.",
                resource_type="report",
                primary_topic=cls.topic,
                live=True,
                first_published_at=now + timedelta(days=1),
                body=[("paragraph", "<p>Restricted content.</p>")],
            )
        )
        PageViewRestriction.objects.create(
            page=cls.private, restriction_type=PageViewRestriction.LOGIN
        )
        cls.resources[0].keywords.add("internal-keyword-never-on-library")
        cls.resources[0].save()

    def setUp(self):
        self.factory = RequestFactory()
        Site.clear_site_root_paths_cache()
        self.addCleanup(Site.clear_site_root_paths_cache)

    def context(self, **query):
        request = self.factory.get(self.library.url, query)
        return self.library.get_context(request)

    def test_recent_resources_are_public_and_sorted_by_when_first_added(self):
        recent = self.context()["recent_resources"]
        self.assertEqual(recent.paginator.count, 21)
        self.assertEqual(recent.paginator.per_page, 20)
        self.assertEqual(list(recent), self.resources[:20])
        self.assertEqual(recent[0].primary_topic.pk, self.topic.pk)
        self.assertEqual(recent[0].get_resource_type_display(), "Guideline")
        self.assertEqual(recent[0].reading_time, 2)

    def test_page_size_accepts_only_the_three_offered_values(self):
        for selected in (20, 50, 100):
            with self.subTest(selected=selected):
                context = self.context(per_page=str(selected))
                self.assertEqual(context["recent_per_page"], selected)
                self.assertEqual(context["recent_resources"].paginator.per_page, selected)
                self.assertEqual(len(context["recent_resources"]), min(selected, 21))
        for invalid in ("", "1", "-20", "21", "999999", "many"):
            with self.subTest(invalid=invalid):
                context = self.context(per_page=invalid)
                self.assertEqual(context["recent_per_page"], 20)
                self.assertEqual(context["recent_resources"].paginator.per_page, 20)

    def test_page_selection_handles_invalid_and_out_of_range_values(self):
        self.assertEqual(list(self.context(page="2")["recent_resources"]), self.resources[20:])
        self.assertEqual(self.context(page="not-a-number")["recent_resources"].number, 1)
        self.assertEqual(self.context(page="99999")["recent_resources"].number, 2)
        self.assertEqual(self.context(page="-1")["recent_resources"].number, 2)

    def test_restrictions_on_the_resource_parent_also_hide_cards(self):
        PageViewRestriction.objects.create(
            page=self.resource_index, restriction_type=PageViewRestriction.LOGIN
        )
        self.assertEqual(self.context()["recent_resources"].paginator.count, 0)

    def test_library_renders_real_cards_without_drafts_restricted_pages_or_keywords(self):
        response = self.client.get(self.library.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.resources[0].title)
        self.assertContains(response, self.resources[0].url)
        self.assertContains(response, self.resources[0].short_summary)
        self.assertNotContains(response, self.draft.title)
        self.assertNotContains(response, self.private.title)
        self.assertNotContains(response, "internal-keyword-never-on-library")
