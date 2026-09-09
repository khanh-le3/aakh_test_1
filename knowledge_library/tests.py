from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from wagtail.models import Page, Site

from .models import KnowledgeLibraryPage, TopicCard
from .topics import TOPICS, TOPIC_KEYS


class KnowledgeLibraryTests(TestCase):
    def setUp(self):
        # Database rollbacks do not clear site URLs cached by earlier tests.
        Site.clear_site_root_paths_cache()
        self.addCleanup(Site.clear_site_root_paths_cache)
        self.page = KnowledgeLibraryPage.objects.get()

    def page_form_data(self):
        cards = list(self.page.topic_cards.all())
        data = {
            "title": self.page.title,
            "slug": self.page.slug,
            "banner_intro": "An updated introduction to the knowledge library.",
            "topics_intro": "Choose a topic to explore.",
            "topic_cards-TOTAL_FORMS": str(len(cards)),
            "topic_cards-INITIAL_FORMS": str(len(cards)),
            "topic_cards-MIN_NUM_FORMS": "12",
            "topic_cards-MAX_NUM_FORMS": "12",
        }
        for index, card in enumerate(cards):
            for field in ("id", "name", "summary", "icon"):
                value = getattr(card, field)
                data[f"topic_cards-{index}-{field}"] = "" if value is None else str(value)
            data[f"topic_cards-{index}-ORDER"] = str(index)
        return data

    def page_form(self, data):
        form_class = KnowledgeLibraryPage.get_edit_handler().get_form_class()
        return form_class(
            data=data, instance=self.page, parent_page=self.page.get_parent()
        )

    def test_seed_has_all_fixed_topics_in_order(self):
        self.assertEqual(self.page.get_parent().specific_class.__name__, "HomePage")
        self.assertEqual(self.page.url, "/knowledge-library/")
        self.assertTrue(self.page.live)
        self.assertEqual(
            list(self.page.topic_cards.values_list("topic_key", flat=True)),
            [key for key, _name, _icon, _summary in TOPICS],
        )
        self.assertEqual(Page.find_problems(), ([], [], [], [], []))

    @override_settings(DEBUG=False)
    def test_published_page_uses_wagtail_in_production(self):
        self.assertEqual(resolve("/knowledge-library/").url_name, "wagtail_serve")
        response = self.client.get("/knowledge-library/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "knowledge_library/knowledge_library_page.html"
        )
        for card in self.page.topic_cards.all():
            self.assertContains(response, card.name)
            self.assertContains(response, card.summary)
            self.assertContains(response, card.url)

    @override_settings(DEBUG=False)
    def test_unpublished_page_is_not_a_public_static_preview(self):
        self.page.live = False
        self.page.save(update_fields=["live"])
        self.assertEqual(self.client.get("/knowledge-library/").status_code, 404)

    def test_card_lengths_and_icon_choice_are_validated(self):
        for field, value in (
            ("name", "a" * 61),
            ("summary", "a" * 161),
            ("icon", "../../unrecognised"),
        ):
            with self.subTest(field=field):
                card = self.page.topic_cards.first()
                setattr(card, field, value)
                with self.assertRaises(ValidationError) as error:
                    card.full_clean()
                self.assertIn(field, error.exception.message_dict)

    def test_existing_card_identity_cannot_change(self):
        card = self.page.topic_cards.first()
        card.topic_key = "diagnosis-and-assessment"
        with self.assertRaisesMessage(ValidationError, "fixed topic cannot be changed"):
            card.clean()

    def test_revision_keeps_card_changes_unpublished_until_publish(self):
        original_intro = self.page.banner_intro
        card = self.page.topic_cards.first()
        original_name = card.name
        self.page.banner_intro = "A saved draft introduction."
        self.page.topics_intro = "A saved draft topic introduction."
        card.name = "Learning about autism"
        card.summary = "A saved draft topic summary."
        card.icon = "school"
        self.page.topic_cards.add(card)
        revision = self.page.save_revision()

        live_page = KnowledgeLibraryPage.objects.get(pk=self.page.pk)
        self.assertEqual(live_page.banner_intro, original_intro)
        self.assertEqual(live_page.topic_cards.get(pk=card.pk).name, original_name)
        draft_page = revision.as_object()
        draft_card = draft_page.topic_cards.get(id=card.pk)
        self.assertEqual(draft_card.name, "Learning about autism")
        self.assertEqual(draft_card.icon_name, "topic-school")
        self.assertEqual(draft_card.topic_key, "understanding-autism")
        self.assertEqual(draft_card.url, card.url)

        revision.publish()
        live_page.refresh_from_db()
        self.assertEqual(live_page.banner_intro, "A saved draft introduction.")
        self.assertEqual(live_page.topics_intro, "A saved draft topic introduction.")
        live_card = live_page.topic_cards.get(pk=card.pk)
        self.assertEqual(live_card.name, "Learning about autism")
        self.assertEqual(live_card.summary, "A saved draft topic summary.")
        self.assertEqual(live_card.icon, "school")

    def test_revision_rejects_missing_topic(self):
        self.page.topic_cards.remove(self.page.topic_cards.first())
        with self.assertRaisesMessage(ValidationError, "12 fixed topics"):
            self.page.save_revision()

    def test_admin_form_edits_copy_without_exposing_taxonomy(self):
        data = self.page_form_data()
        data["topic_cards-0-name"] = "Autism information"
        data["topic_cards-0-summary"] = "An edited summary."
        data["topic_cards-0-icon"] = "school"
        data["topic_cards-0-topic_key"] = "arbitrary-editor-topic"
        form = self.page_form(data)
        self.assertTrue(form.is_valid(), (form.errors, form.formsets["topic_cards"].errors))
        self.assertNotIn("topic_key", form.formsets["topic_cards"].forms[0].fields)
        updated_page = form.save(commit=False)
        card = updated_page.topic_cards.all()[0]
        self.assertEqual(card.name, "Autism information")
        self.assertEqual(card.summary, "An edited summary.")
        self.assertEqual(card.icon, "school")
        self.assertEqual(card.topic_key, "understanding-autism")
        self.assertEqual(set(updated_page.topic_cards.values_list("topic_key", flat=True)), TOPIC_KEYS)

    def test_wagtail_editor_renders_card_controls(self):
        editor = get_user_model().objects.create_user(
            username="library-editor", is_staff=True, is_superuser=True
        )
        self.client.force_login(editor)
        response = self.client.get(
            reverse("wagtailadmin_pages:edit", args=[self.page.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="banner_intro"')
        self.assertContains(response, 'name="topics_intro"')
        self.assertContains(response, 'name="topic_cards-11-name"')
        self.assertContains(response, 'name="topic_cards-11-summary"')
        self.assertContains(response, 'name="topic_cards-11-icon"')
        self.assertNotContains(response, 'name="topic_cards-0-topic_key"')

    def test_editor_can_recreate_the_page_with_all_fixed_topics(self):
        homepage = self.page.get_parent()
        self.page.delete()
        homepage.refresh_from_db()
        self.page = KnowledgeLibraryPage(
            title="Knowledge library", slug="knowledge-library"
        )
        form_class = KnowledgeLibraryPage.get_edit_handler().get_form_class()
        unbound_form = form_class(instance=self.page, parent_page=homepage)
        cards_formset = unbound_form.formsets["topic_cards"]
        self.assertEqual(len(cards_formset.forms), 12)
        self.assertEqual(cards_formset.forms[0].instance.topic_key, "understanding-autism")
        self.assertEqual(cards_formset.forms[0].initial["name"], "Understanding autism")

        data = self.page_form_data()
        data["topic_cards-0-name"] = "New autism information"
        data["topic_cards-0-topic_key"] = "arbitrary-topic"
        # Simulate a fresh POST request with a newly constructed page instance.
        form = form_class(
            data=data, instance=KnowledgeLibraryPage(), parent_page=homepage
        )
        self.assertTrue(form.is_valid(), (form.errors, form.formsets["topic_cards"].errors))
        created_page = form.save(commit=False)
        homepage.add_child(instance=created_page)
        created_page.save_revision().publish()
        created_page.refresh_from_db()
        self.assertEqual(created_page.topic_cards.count(), 12)
        self.assertEqual(created_page.topic_cards.first().name, "New autism information")
        self.assertEqual(
            set(created_page.topic_cards.values_list("topic_key", flat=True)), TOPIC_KEYS
        )

    def test_admin_form_rejects_overlong_copy(self):
        data = self.page_form_data()
        data["topic_cards-0-name"] = "a" * 61
        data["topic_cards-0-summary"] = "a" * 161
        form = self.page_form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.formsets["topic_cards"].forms[0].errors)
        self.assertIn("summary", form.formsets["topic_cards"].forms[0].errors)

    def test_admin_form_rejects_deleted_topic(self):
        data = self.page_form_data()
        data["topic_cards-0-DELETE"] = "on"
        form = self.page_form(data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.formsets["topic_cards"].non_form_errors())

    def test_admin_form_rejects_duplicate_card_id(self):
        data = self.page_form_data()
        data["topic_cards-1-id"] = data["topic_cards-0-id"]
        form = self.page_form(data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.formsets["topic_cards"].non_form_errors())

    def test_seed_migration_preserves_existing_editor_copy(self):
        self.page.banner_intro = "An editor has changed this introduction."
        self.page.save()
        migration = import_module(
            "knowledge_library.migrations.0002_create_knowledge_library"
        )
        with connection.schema_editor() as schema_editor:
            migration.create_knowledge_library(apps, schema_editor)
        self.page.refresh_from_db()
        self.assertEqual(self.page.banner_intro, "An editor has changed this introduction.")
        self.assertEqual(KnowledgeLibraryPage.objects.count(), 1)
        self.assertEqual(TopicCard.objects.filter(page=self.page).count(), 12)

    def test_seed_migration_preserves_conflicting_page(self):
        homepage = self.page.get_parent()
        self.page.delete()
        homepage.refresh_from_db()
        existing = homepage.add_child(
            instance=Page(title="An existing library", slug="knowledge-library")
        )
        migration = import_module(
            "knowledge_library.migrations.0002_create_knowledge_library"
        )
        with connection.schema_editor() as schema_editor:
            migration.create_knowledge_library(apps, schema_editor)
        self.assertFalse(KnowledgeLibraryPage.objects.exists())
        self.assertEqual(Page.objects.get(pk=existing.pk).title, "An existing library")
