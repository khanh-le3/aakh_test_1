"""Developer-owned topic identities and starter card copy.

Editors can change the display copy and icon without changing the topic's key,
reserved URL, or colour. Cross-cutting remains a working topic name; its eventual
scope is not defined by this presentation model.
"""

#Topics are fixed identities, not editable by editors. Each topic has a key. DO NOT change the keys. The keys are
#used in URLs and in the database.
TOPICS = (
    ("understanding-autism", "Understanding autism", "understanding",
     "Autism characteristics, development, thinking, genetics and brain research"),
    ("diagnosis-and-assessment", "Diagnosis and assessment", "diagnosis",
     "Recognising autism, experiences of diagnosis, and assessing strengths and support needs"),
    ("communication-sensory-and-movement", "Communication, sensory and movement", "communication",
     "Ways of communicating, communication supports, sensory differences and sensory environments"),
    ("therapies-supports-and-services", "Therapies, supports and services", "supports",
     "Evidence about therapies and support approaches, and accessing and improving services"),
    ("education-and-learning", "Education and learning", "school",
     "Early learning, school, TAFE, university and lifelong education"),
    ("work-and-employment", "Work and employment", "adulthood",
     "Finding and keeping work, workplace experiences, adjustments and career development"),
    ("physical-health-and-healthcare", "Physical health and healthcare", "health",
     "Sleep, eating, physical health conditions, healthy living and access to healthcare"),
    ("mental-health-and-wellbeing", "Mental health and wellbeing", "wellbeing",
     "Emotional wellbeing, anxiety, depression, burnout and mental healthcare"),
    ("family-relationships-and-social-life", "Family, relationships and social life", "relationships",
     "Family life, parenting, carers, friendships, intimate relationships and social connection"),
    ("daily-life-and-housing", "Daily life and housing", "daily-life",
     "Daily activities, transport, leisure, housing and living with the support people choose"),
    ("inclusion-rights-and-safety", "Inclusion, rights and safety", "inclusion",
     "Acceptance, accessibility, discrimination, safeguarding, advocacy and justice"),
    ("cross-cutting", "Cross-cutting", "cross-cutting",
     "Explore information that connects several topics across the knowledge library"),
)

TOPIC_CHOICES = tuple((key, name) for key, name, _icon, _summary in TOPICS)
TOPIC_KEYS = frozenset(key for key, _name in TOPIC_CHOICES)
TOPIC_COUNT = len(TOPICS)

# Single source of truth for topic-to-accent assignments. These stable slot IDs
# select --color-topic-accent-<id> in tokens.css through aakh.css card variants.
# Assign by fixed key, never by the editable name, icon or display order.
# Change a value here to reassign an accent; change tokens.css to edit its colour.
TOPIC_ACCENTS = {
    "understanding-autism": "01",
    "diagnosis-and-assessment": "02",
    "communication-sensory-and-movement": "03",
    "therapies-supports-and-services": "04",
    "education-and-learning": "05",
    "work-and-employment": "06",
    "physical-health-and-healthcare": "07",
    "mental-health-and-wellbeing": "08",
    "family-relationships-and-social-life": "09",
    "daily-life-and-housing": "10",
    "inclusion-rights-and-safety": "11",
    "cross-cutting": "12",
}

ICON_CHOICES = (
    ("understanding", "Understanding autism"),
    ("diagnosis", "Diagnosis and assessment"),
    ("communication", "Communication"),
    ("supports", "Supports and services"),
    ("school", "Education and learning"),
    ("adulthood", "Work and employment"),
    ("health", "Physical health"),
    ("wellbeing", "Mental health and wellbeing"),
    ("relationships", "Relationships"),
    ("daily-life", "Daily life"),
    ("inclusion", "Inclusion and accessibility"),
    ("cross-cutting", "Cross-cutting"),
)

BANNER_INTRO = (
    "Explore plain-language summaries of autism research, alongside practical guidelines, frameworks and reports. "
    "Understand key findings, how much confidence to place in the evidence, and what it could mean in everyday life."
)
TOPICS_INTRO = (
    "Each topic page lists the snapshots, frameworks, guidelines and reports on that topic. "
    "Select a topic that you would like to explore."
)
