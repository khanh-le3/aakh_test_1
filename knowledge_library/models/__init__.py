"""Register library models and preserve their public import paths."""

from .library import KnowledgeLibraryPage, TopicCard
from .resources import (
    ResourceIndexPage,
    ResourcePage,
    ResourcePageForm,
    ResourcePageKeyword,
    validate_resource_topics,
)
# Historical migrations import this mixin from knowledge_library.models.
from .shared import FixedLibraryPathMixin, library_context, resource_listing_context
from .topics import TopicIndexPage, TopicPage

__all__ = [
    "FixedLibraryPathMixin",
    "KnowledgeLibraryPage",
    "ResourceIndexPage",
    "ResourcePage",
    "ResourcePageForm",
    "ResourcePageKeyword",
    "TopicCard",
    "TopicIndexPage",
    "TopicPage",
    "library_context",
    "resource_listing_context",
    "validate_resource_topics",
]
