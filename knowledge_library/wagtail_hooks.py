"""Resource-only text formatting, stored as theme-aware semantic classes."""

from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.admin.rich_text.editors.draftail.features import InlineStyleFeature


@hooks.register("register_rich_text_features")
def register_resource_text_colours(features):
    features.register_editor_plugin("draftail", "underline", InlineStyleFeature({
        "type": "UNDERLINE", "label": "U", "description": "Underline",
    }))
    features.register_converter_rule("contentstate", "underline", {
        "from_database_format": {"u": InlineStyleElementHandler("UNDERLINE")},
        "to_database_format": {"style_map": {"UNDERLINE": "u"}},
    })
    for name, label, description, editor_colour in (
        ("primary", "N", "Navy text (adapts to the reader's theme)", "var(--w-color-text-label)"),
        ("secondary", "T", "Teal text (adapts to the reader's theme)", "var(--w-color-text-link)"),
    ):
        feature_name = f"resource-{name}"
        style_type = f"RESOURCE_{name.upper()}"
        css_class = f"resource-text resource-text--{name}"
        features.register_editor_plugin("draftail", feature_name, InlineStyleFeature({
            "type": style_type,
            "label": label,
            "description": description,
            "style": {"color": editor_colour},
        }))
        features.register_converter_rule("contentstate", feature_name, {
            "from_database_format": {
                f'span[class="{css_class}"]': InlineStyleElementHandler(style_type),
            },
            "to_database_format": {
                "style_map": {style_type: {"element": "span", "props": {"class": css_class}}},
            },
        })
    # Keep these out of default_features: only the resource paragraph opts in.
