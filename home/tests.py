from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from home.models import HomePage
from knowledge_library.models import KnowledgeLibraryPage

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase


class HomeSetUpTests(WagtailPageTestCase):
    """
    Tests for basic page structure setup and HomePage creation.
    """

    def test_root_create(self):
        root_page = Page.objects.get(pk=1)
        self.assertIsNotNone(root_page)

    def test_homepage_create(self):
        root_page = Page.objects.get(pk=1)
        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)
        self.assertTrue(HomePage.objects.filter(title="Home").exists())


class HomeTests(WagtailPageTestCase):
    """
    Tests for homepage functionality and rendering.
    """

    def setUp(self):
        """
        Create a homepage instance for testing.
        """
        root_page = Page.get_first_root_node()
        Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.homepage = HomePage(title="Home")
        root_page.add_child(instance=self.homepage)

    def test_homepage_is_renderable(self):
        self.assertPageIsRenderable(self.homepage)

    def test_homepage_template_used(self):
        response = self.client.get(self.homepage.url)
        self.assertTemplateUsed(response, "home/home_page.html")


class HeroSeedTests(TestCase):
    def setUp(self):
        self.homepage = HomePage.objects.get(slug="home")
        self.library = KnowledgeLibraryPage.objects.get(slug="knowledge-library")

    def seed(self):
        migration = import_module("home.migrations.0007_seed_hero_content")
        migration.seed_hero_content(apps, SimpleNamespace(connection=connection))
        self.homepage.refresh_from_db()

    def test_fresh_database_has_renderable_hero_and_library_link(self):
        self.assertEqual(self.homepage.hero_heading, "Autism research")
        self.assertEqual(self.homepage.hero_heading_line_2, "you can use")
        self.assertEqual(self.homepage.hero_cta_primary_page_id, self.library.pk)
        response = self.client.get("/")
        self.assertContains(response, "Welcome to the Australian Autism Knowledge Hub")
        self.assertContains(response, 'href="/knowledge-library/"')
        self.assertIsNone(self.homepage.hero_cta_secondary_page_id)

    def test_existing_unedited_homepage_is_seeded_and_can_be_published(self):
        HomePage.objects.filter(pk=self.homepage.pk).update(
            hero_heading="Autism research you can use",
            hero_heading_line_2="",
            hero_intro="",
            hero_cta_primary_page=None,
        )
        self.seed()
        self.assertEqual(self.homepage.hero_heading, "Autism research")
        self.assertEqual(self.homepage.hero_heading_line_2, "you can use")
        self.assertTrue(self.homepage.hero_intro)
        self.assertEqual(self.homepage.hero_cta_primary_page_id, self.library.pk)
        self.homepage.save_revision().publish()
        self.homepage.refresh_from_db()
        self.assertIn("Welcome to the Australian Autism Knowledge Hub", self.homepage.hero_intro)

    def test_rerun_preserves_custom_copy_and_destination(self):
        self.homepage.hero_heading = "Custom heading"
        self.homepage.hero_heading_line_2 = ""
        self.homepage.hero_intro = "<p>Custom introduction</p>"
        self.homepage.hero_cta_primary_page = self.homepage
        self.homepage.hero_cta_primary_label = "Custom label"
        self.homepage.save()
        for _ in range(2):
            self.seed()
        self.assertEqual(self.homepage.hero_heading, "Custom heading")
        self.assertEqual(self.homepage.hero_heading_line_2, "")
        self.assertEqual(self.homepage.hero_intro, "<p>Custom introduction</p>")
        self.assertEqual(self.homepage.hero_cta_primary_page_id, self.homepage.pk)
        self.assertEqual(self.homepage.hero_cta_primary_label, "Custom label")

    def test_saved_editorial_revision_is_untouched_including_blank_fields(self):
        self.homepage.hero_intro = ""
        self.homepage.hero_cta_primary_page = None
        self.homepage.save_revision().publish()
        self.homepage.hero_heading = "An unpublished heading"
        draft = self.homepage.save_revision()
        self.seed()
        self.assertEqual(self.homepage.hero_intro, "")
        self.assertIsNone(self.homepage.hero_cta_primary_page_id)
        self.assertEqual(self.homepage.latest_revision_id, draft.pk)
        self.assertEqual(
            self.homepage.get_latest_revision_as_object().hero_heading,
            "An unpublished heading",
        )
