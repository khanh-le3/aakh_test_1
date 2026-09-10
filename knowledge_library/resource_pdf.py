"""Readable, tagged PDF exports of the published resource content."""

from hashlib import sha256
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from weasyprint import HTML
from weasyprint.urls import URLFetcher, URLFetcherResponse

from .resource_content import resource_content_context


ASSET_ORIGIN = "https://resource-pdf.invalid/"
STATIC_ASSETS = {
    "static/css/tokens.css": ("css/tokens.css", "text/css"),
    "static/knowledge_library/css/resource-pdf.css": (
        "knowledge_library/css/resource-pdf.css", "text/css"
    ),
    "static/fonts/lexend-latin-var.woff2": ("fonts/lexend-latin-var.woff2", "font/woff2"),
}


def resource_pdf_html(page, request):
    """Reuse the web content's semantics and anchors, with printable media."""
    context = resource_content_context(page.body)
    soup = BeautifulSoup(str(context["resource_body"]), "html.parser")
    # The full transcripts and labelled links remain in their reading order.
    for player in soup.select("audio, video"):
        player.decompose()
    for icon in soup.select('svg[aria-hidden="true"]'):
        icon.decompose()
    for element in soup.select("[tabindex]"):
        del element["tabindex"]
    for region in soup.select(".resource-content__table-scroll"):
        region.attrs.pop("role", None)
        region.attrs.pop("aria-label", None)
    for image in soup.select("img"):
        # WeasyPrint tags even empty-alt images as figures. Omit decoration
        # so PDF readers do not encounter undescribed, meaningless figures.
        if not image.get("alt"):
            image.decompose()
        else:
            image.attrs.pop("loading", None)

    # A wide table cannot scroll on paper. Preserve every row/column pairing
    # in labelled records instead of shrinking text to an unreadable size.
    for table in soup.select("table"):
        headers = table.select("thead th")
        if len(headers) <= 4:
            continue
        records = soup.new_tag("div", attrs={"class": "resource-pdf__records"})
        caption = soup.new_tag("p")
        strong = soup.new_tag("strong")
        strong.string = table.caption.get_text()
        caption.append(strong)
        records.append(caption)
        for index, row in enumerate(table.select("tbody tr"), start=1):
            label = soup.new_tag("p", attrs={"class": "resource-pdf__row-label"})
            label.string = f"Row {index}"
            records.append(label)
            listing = soup.new_tag("dl")
            for header, cell in zip(headers, row.find_all(["td", "th"], recursive=False)):
                term, value = soup.new_tag("dt"), soup.new_tag("dd")
                term.string = header.get_text()
                value.extend(list(cell.contents))
                listing.extend([term, value])
            records.append(listing)
        table.replace_with(records)

    source_url = request.build_absolute_uri(page.get_url(request))
    return render_to_string(
        "knowledge_library/resource_pdf.html",
        {
            "page": page,
            "topics": page.topics,
            "resource_body": mark_safe(str(soup)),
            "resource_toc": context["resource_toc"],
            "source_url": source_url,
            "site_name": settings.WAGTAIL_SITE_NAME,
            "asset_origin": ASSET_ORIGIN,
        },
    )


def _static_bytes(name):
    # Works both with source staticfiles and a collected (possibly remote)
    # staticfiles storage. Never interpret resource content as a local path.
    source = finders.find(name)
    if source:
        return Path(source).read_bytes()
    with staticfiles_storage.open(name, "rb") as asset:
        return asset.read()


class ResourcePDFFetcher(URLFetcher):
    """Only read explicit assets; never perform renderer-initiated I/O."""

    def __init__(self, assets):
        super().__init__(allowed_protocols=())
        self.assets = assets

    def fetch(self, url, headers=None):
        if url not in self.assets:
            raise ValueError("This asset is not part of the resource PDF.")
        content, mime_type = self.assets[url]
        return URLFetcherResponse(url, content, {"Content-Type": mime_type})


def render_resource_pdf(page, request):
    """Render with embedded fonts, reading-order tags, language and bookmarks."""
    source_url = request.build_absolute_uri(page.get_url(request))
    markup = resource_pdf_html(page, request)
    assets = {
        urljoin(ASSET_ORIGIN, url): (_static_bytes(name), mime_type)
        for url, (name, mime_type) in STATIC_ASSETS.items()
    }
    # Resolve only images chosen in this resource, through their configured
    # Wagtail storage. No network, arbitrary file, CSS or attachment URLs from
    # content are delegated to WeasyPrint's default URL fetcher.
    for block in page.body:
        if block.block_type == "image" and not block.value["decorative"]:
            rendition = block.value["image"].get_rendition("width-1200")
            with rendition.file.open("rb") as asset:
                assets[urljoin(source_url, rendition.url)] = (
                    asset.read(), f"image/{rendition.file.name.rsplit('.', 1)[-1].lower()}"
                )
    digest = sha256(markup.encode())
    for url, (content, mime_type) in sorted(assets.items()):
        digest.update(url.encode())
        digest.update(content)
    cache_key = f"resource-pdf-v1:{digest.hexdigest()}"
    pdf = cache.get(cache_key)
    if pdf is None:
        pdf = HTML(
            string=markup, base_url=source_url, url_fetcher=ResourcePDFFetcher(assets)
        ).write_pdf(pdf_variant="pdf/ua-1", pdf_tags=True)
        cache.set(cache_key, pdf, timeout=900)
    return pdf
