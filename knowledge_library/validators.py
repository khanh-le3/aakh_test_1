"""Reusable editorial word limits, including validation outside the admin."""

import re

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class MaxWordsValidator:
    def __init__(self, limit):
        self.limit = limit

    def __call__(self, value):
        count = len(re.findall(r"\S+", str(value or "")))
        if count > self.limit:
            raise ValidationError(
                "Use no more than %(limit)s words (currently %(count)s).",
                code="max_words",
                params={"limit": self.limit, "count": count},
            )

    def __eq__(self, other):
        return isinstance(other, MaxWordsValidator) and self.limit == other.limit
