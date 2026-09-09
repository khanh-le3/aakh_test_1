"""Published resources drive the library's recently added section."""

from datetime import date, timedelta

from bs4 import BeautifulSoup
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
        cls.secondary_topics = list(
            TopicPage.objects.exclude(pk=cls.topic.pk).order_by("path")[:2]
        )
        cls.resources[0].secondary_topics.set(cls.secondary_topics)
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
        self.assertEqual(list(recent), self.resources[:10])
        self.assertEqual(recent[0].primary_topic.pk, self.topic.pk)
        self.assertEqual(recent[0].get_resource_type_display(), "Guideline")
        self.assertEqual(recent[0].reading_time, 2)

    def test_old_pagination_parameters_do_not_change_the_latest_ten(self):
        for query in (
            {"page": "2", "per_page": "50"},
            {"page": "99999", "per_page": "100"},
            {"page": "not-a-number", "per_page": "many"},
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    list(self.context(**query)["recent_resources"]), self.resources[:10]
                )

    def test_restrictions_on_the_resource_parent_also_hide_cards(self):
        PageViewRestriction.objects.create(
            page=self.resource_index, restriction_type=PageViewRestriction.LOGIN
        )
        self.assertEqual(list(self.context()["recent_resources"]), [])

    def test_library_renders_real_cards_without_drafts_restricted_pages_or_keywords(self):
        response = self.client.get(self.library.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.resources[0].title)
        self.assertContains(response, self.resources[0].url)
        self.assertContains(response, self.resources[0].short_summary)
        self.assertNotContains(response, self.draft.title)
        self.assertNotContains(response, self.private.title)
        self.assertNotContains(response, "internal-keyword-never-on-library")

    def test_recent_cards_link_once_and_include_all_topics_with_primary_first(self):
        response = self.client.get(self.library.url)
        section = BeautifulSoup(response.content, "html.parser").select_one(
            "#recently-added"
        )
        cards = section.select(".card--recent")
        self.assertEqual(len(cards), 10)
        self.assertFalse(section.select(".pagination, select"))
        for card, resource in zip(cards, self.resources):
            with self.subTest(resource=resource.title):
                self.assertEqual(card.name, "a")
                self.assertEqual(card["href"], resource.url)
                self.assertFalse(card.select("a, button, input, [tabindex]"))
                heading = card.find(id=card["aria-labelledby"])
                self.assertEqual(heading.get_text(), resource.title)
        topics = cards[0].select(".card__topics .tag")
        self.assertEqual(topics[0].get_text(), self.topic.title)
        self.assertCountEqual(
            [topic.get_text() for topic in topics[1:]],
            [topic.title for topic in self.secondary_topics],
        )
        self.assertEqual(len(cards[1].select(".card__topics .tag")), 1)

    def test_card_topics_are_prefetched(self):
        recent = list(self.context()["recent_resources"])
        with self.assertNumQueries(0):
            for resource in recent:
                self.assertEqual(resource.primary_topic.pk, self.topic.pk)
                list(resource.secondary_topics.all())
