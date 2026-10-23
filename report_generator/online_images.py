"""Search and download openly licensed images from Wikimedia Commons."""

from html import unescape
from io import BytesIO
import re
from urllib.parse import urlparse

import requests
from PIL import Image, UnidentifiedImageError

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
ALLOWED_IMAGE_HOSTS = {"upload.wikimedia.org", "commons.wikimedia.org"}


def search_wikimedia_images(query, limit=6):
    """Return Wikimedia Commons image results with available attribution metadata."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Enter a topic to search for images.")

    try:
        response = requests.get(
            COMMONS_API_URL,
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": 6,
                "gsrlimit": max(1, min(int(limit), 10)),
                "prop": "imageinfo|info",
                "inprop": "url",
                "iiprop": "url|extmetadata",
                "iiurlwidth": 900,
                "format": "json",
            },
            headers={"User-Agent": "DocScholarReportGenerator/1.0 (educational project)"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Could not reach Wikimedia Commons. Check your internet connection and try again.") from error

    try:
        pages = response.json().get("query", {}).get("pages", {})
    except (AttributeError, ValueError) as error:
        raise ValueError("Wikimedia Commons returned an unreadable response.") from error

    results = []
    for page in pages.values():
        image_info_list = page.get("imageinfo") or []
        if not image_info_list:
            continue

        info = image_info_list[0]
        thumbnail_url = info.get("thumburl") or info.get("url")
        if not thumbnail_url or not _is_allowed_image_url(thumbnail_url):
            continue

        metadata = info.get("extmetadata") or {}
        artist = _metadata_value(metadata, "Artist")
        license_name = _metadata_value(metadata, "LicenseShortName")
        license_url = _metadata_value(metadata, "LicenseUrl")

        results.append({
            "title": page.get("title", "Wikimedia image"),
            "thumbnail_url": thumbnail_url,
            "download_url": thumbnail_url,
            "source_url": page.get("fullurl") or (
                "https://commons.wikimedia.org/wiki/" +
                page.get("title", "").replace(" ", "_")
            ),
            "artist": artist,
            "license": license_name,
            "license_url": license_url,
        })

    return results


def download_wikimedia_image(image_result):
    """Download a Commons thumbnail and convert it to PNG bytes for Word."""
    image_url = image_result.get("download_url") or image_result.get("thumbnail_url")
    if not image_url or not _is_allowed_image_url(image_url):
        raise ValueError("This image does not have a trusted Wikimedia Commons URL.")

    try:
        response = requests.get(
            image_url,
            headers={"User-Agent": "DocScholarReportGenerator/1.0 (educational project)"},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Could not download this image from Wikimedia Commons. Please try another image.") from error

    try:
        with Image.open(BytesIO(response.content)) as image:
            image.load()
            if image.width < 1 or image.height < 1:
                raise ValueError("The selected image has invalid dimensions.")
            image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Wikimedia Commons returned an image format we could not read.") from error


def _metadata_value(metadata, key):
    """Read a Commons metadata field without its HTML markup."""
    value = metadata.get(key, {})
    if not isinstance(value, dict):
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", str(value.get("value", "")))).strip()


def _is_allowed_image_url(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_IMAGE_HOSTS
