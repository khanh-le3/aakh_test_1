"""Create the canonical resource parent and fixed topic browse destinations."""

from django.db import migrations, models
from django.utils import timezone


# Frozen identities. Editor copy is taken from the existing library cards below.
TOPICS = (
    ("understanding-autism", "Understanding autism"),
    ("diagnosis-and-assessment", "Diagnosis and assessment"),
    ("communication-sensory-and-movement", "Communication, sensory and movement"),
    ("therapies-supports-and-services", "Therapies, supports and services"),
    ("education-and-learning", "Education and learning"),
    ("work-and-employment", "Work and employment"),
    ("physical-health-and-healthcare", "Physical health and healthcare"),
    ("mental-health-and-wellbeing", "Mental health and wellbeing"),
    ("family-relationships-and-social-life", "Family, relationships and social life"),
    ("daily-life-and-housing", "Daily life and housing"),
    ("inclusion-rights-and-safety", "Inclusion, rights and safety"),
    ("cross-cutting", "Cross-cutting"),
)


def create_resource_structure(apps, schema_editor):
    database = schema_editor.connection.alias
    Page = apps.get_model("wagtailcore", "Page")
    ContentType = apps.get_model("contenttypes", "ContentType")
    LibraryPage = apps.get_model("knowledge_library", "KnowledgeLibraryPage")
    TopicCard = apps.get_model("knowledge_library", "TopicCard")
    TopicIndexPage = apps.get_model("knowledge_library", "TopicIndexPage")
    TopicPage = apps.get_model("knowledge_library", "TopicPage")
    ResourceIndexPage = apps.get_model("knowledge_library", "ResourceIndexPage")

    library = LibraryPage.objects.using(database).order_by("path").first()
    if library is None:
        return

    def ensure_child(parent, model, slug, title, **fields):
        children = Page.objects.using(database).filter(
            path__startswith=parent.path, depth=parent.depth + 1
        )
        existing = children.filter(slug=slug).first()
        if existing:
            # Preserve existing copy and any page occupying a reserved URL.
            return model.objects.using(database).filter(pk=existing.pk).first()

        last_path = children.order_by("-path").values_list("path", flat=True).first()
        position = int(last_path[-4:], 36) + 1 if last_path else 1
        if position >= 36**4:
            raise RuntimeError("No tree path remains for a knowledge library page.")
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        segment = ""
        while position:
            position, digit = divmod(position, 36)
            segment = alphabet[digit] + segment

        content_type, _created = ContentType.objects.using(database).get_or_create(
            app_label="knowledge_library", model=model._meta.model_name
        )
        now = timezone.now()
        child = model.objects.using(database).create(
            title=title,
            draft_title=title,
            slug=slug,
            content_type_id=content_type.pk,
            path=parent.path + segment.zfill(4),
            depth=parent.depth + 1,
            numchild=0,
            url_path=parent.url_path + slug + "/",
            locale_id=parent.locale_id,
            live=True,
            has_unpublished_changes=False,
            first_published_at=now,
            last_published_at=now,
            **fields,
        )
        Page.objects.using(database).filter(pk=parent.pk).update(
            numchild=models.F("numchild") + 1
        )
        return child

    ensure_child(library, ResourceIndexPage, "resources", "Resources")
    topic_index = ensure_child(library, TopicIndexPage, "topics", "Topics")
    if topic_index is None:
        return
    cards = {
        card.topic_key: card
        for card in TopicCard.objects.using(database).filter(page_id=library.pk)
    }
    for key, title in TOPICS:
        if TopicPage.objects.using(database).filter(topic_key=key).exists():
            continue
        card = cards.get(key)
        ensure_child(
            topic_index,
            TopicPage,
            key,
            card.name if card else title,
            topic_key=key,
            introduction=card.summary if card else "",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge_library", "0003_resource_pages"),
    ]

    operations = [
        # Published descendants and protected resource topic references must be
        # handled deliberately before removing this structure.
        migrations.RunPython(create_resource_structure),
    ]
