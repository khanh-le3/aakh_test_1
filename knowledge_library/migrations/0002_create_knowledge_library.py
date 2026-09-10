from django.db import migrations, models
from django.utils import timezone


# Frozen starter copy: later editor changes must never be overwritten.
TOPICS = (
    ("understanding-autism", "Understanding autism", "understanding", "Learn about autism, autistic experiences and ways of understanding difference."),
    ("diagnosis-and-assessment", "Diagnosis and assessment", "diagnosis", "Explore assessment, diagnosis and what happens before and after a diagnosis."),
    ("communication-sensory-and-movement", "Communication, sensory and movement", "communication", "Find information about communication, sensory experiences and movement."),
    ("therapies-supports-and-services", "Therapies, supports and services", "supports", "Explore therapies, everyday supports and services for autistic people."),
    ("education-and-learning", "Education and learning", "school", "Find information about learning, school, further study and education supports."),
    ("work-and-employment", "Work and employment", "adulthood", "Explore finding work, workplace experiences and support at work."),
    ("physical-health-and-healthcare", "Physical health and healthcare", "health", "Find information about physical health, healthcare visits and access to care."),
    ("mental-health-and-wellbeing", "Mental health and wellbeing", "wellbeing", "Explore mental health, emotional wellbeing and finding support."),
    ("family-relationships-and-social-life", "Family, relationships and social life", "relationships", "Find information about family life, friendships, partners and social connection."),
    ("daily-life-and-housing", "Daily life and housing", "daily-life", "Explore daily routines, living skills, housing and support at home."),
    ("inclusion-rights-and-safety", "Inclusion, rights and safety", "inclusion", "Find information about inclusion, rights, advocacy and staying safe."),
    ("cross-cutting", "Cross-cutting", "cross-cutting", "Explore information that connects several topics across the knowledge library."),
)


def create_knowledge_library(apps, schema_editor):
    database = schema_editor.connection.alias
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")
    HomePage = apps.get_model("home", "HomePage")
    LibraryPage = apps.get_model("knowledge_library", "KnowledgeLibraryPage")
    TopicCard = apps.get_model("knowledge_library", "TopicCard")
    ContentType = apps.get_model("contenttypes", "ContentType")

    if LibraryPage.objects.using(database).exists():
        return

    site = Site.objects.using(database).filter(is_default_site=True).first()
    homepage = (
        HomePage.objects.using(database).filter(pk=site.root_page_id).first()
        if site
        else None
    )
    if homepage is None:
        homepage = HomePage.objects.using(database).order_by("path").first()
    if homepage is None:
        return

    children = Page.objects.using(database).filter(
        path__startswith=homepage.path, depth=homepage.depth + 1
    )
    if children.filter(slug="knowledge-library").exists():
        # Preserve any existing page occupying this URL, whatever its type.
        return

    # Historical models do not expose add_child(). Allocate the next standard
    # Wagtail/treebeard four-character base-36 path segment, then update numchild.
    last_child_path = children.order_by("-path").values_list("path", flat=True).first()
    position = int(last_child_path[-4:], 36) + 1 if last_child_path else 1
    if position >= 36**4:
        raise RuntimeError("No tree path remains for the knowledge library page.")
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    segment = ""
    while position:
        position, digit = divmod(position, 36)
        segment = alphabet[digit] + segment

    content_type, _created = ContentType.objects.using(database).get_or_create(
        app_label="knowledge_library", model="knowledgelibrarypage"
    )
    now = timezone.now()
    library = LibraryPage.objects.using(database).create(
        title="Knowledge library",
        draft_title="Knowledge library",
        slug="knowledge-library",
        content_type_id=content_type.pk,
        path=homepage.path + segment.zfill(4),
        depth=homepage.depth + 1,
        numchild=0,
        url_path=homepage.url_path + "knowledge-library/",
        locale_id=homepage.locale_id,
        live=True,
        has_unpublished_changes=False,
        first_published_at=now,
        last_published_at=now,
    )
    TopicCard.objects.using(database).bulk_create(
        [
            TopicCard(
                page_id=library.pk,
                sort_order=order,
                topic_key=key,
                name=name,
                icon=icon,
                summary=summary,
            )
            for order, (key, name, icon, summary) in enumerate(TOPICS)
        ]
    )
    Page.objects.using(database).filter(pk=homepage.pk).update(
        numchild=models.F("numchild") + 1
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0004_hero_heading_lines"),
        ("knowledge_library", "0001_initial"),
    ]

    operations = [
        # Reversing the schema would leave the base Wagtail Page row behind.
        # Require a deliberate content migration before removing these models.
        migrations.RunPython(create_knowledge_library),
    ]
