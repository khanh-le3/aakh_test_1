from django.core.exceptions import ValidationError
from modelcluster.forms import BaseChildFormSet
from wagtail.admin.panels import InlinePanel

from .topics import TOPICS, TOPIC_COUNT, TOPIC_KEYS


def validate_topic_keys(keys):
    if len(keys) != TOPIC_COUNT or set(keys) != TOPIC_KEYS:
        raise ValidationError(
            "Keep one card for each of the 12 fixed topics. Topic cards cannot "
            "be added, removed or assigned to a different topic."
        )


class TopicCardFormSet(BaseChildFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if (
            instance is not None
            and instance.pk is None
            and not instance.topic_cards.exists()
        ):
            instance.topic_cards.set(
                [
                    self.model(
                        sort_order=index,
                        topic_key=key,
                        name=name,
                        icon=icon,
                        summary=summary,
                    )
                    for index, (key, name, icon, summary) in enumerate(TOPICS)
                ]
            )
        super().__init__(*args, **kwargs)

    def _construct_form(self, index, **kwargs):
        form = super()._construct_form(index, **kwargs)
        if self.instance.pk is None and index < TOPIC_COUNT:
            # New child forms have blank IDs. Modelcluster reconstructs their
            # instances on POST, so restore the developer-owned key by row.
            form.instance.topic_key = TOPICS[index][0]
        return form

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        validate_topic_keys(
            [
                form.instance.topic_key
                for form in self.forms
                if form.cleaned_data and not self._should_delete_form(form)
            ]
        )


class TopicCardsPanel(InlinePanel):
    def get_form_options(self):
        options = super().get_form_options()
        options["formsets"][self.relation_name]["formset"] = TopicCardFormSet
        return options
