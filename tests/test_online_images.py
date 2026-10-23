from io import BytesIO
from unittest.mock import Mock, patch

from PIL import Image
import pytest

from report_generator.online_images import (
    download_wikimedia_image,
    search_wikimedia_images,
)


def test_search_wikimedia_images_returns_source_and_license_metadata():
    response = Mock()
    response.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "title": "File:DC generator.png",
                    "fullurl": "https://commons.wikimedia.org/wiki/File:DC_generator.png",
                    "imageinfo": [{
                        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/example.png",
                        "extmetadata": {
                            "Artist": {"value": "<a>Alex</a>"},
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                        },
                    }],
                }
            }
        }
    }

    with patch("report_generator.online_images.requests.get", return_value=response) as get:
        results = search_wikimedia_images("DC generator")

    assert len(results) == 1
    assert results[0]["title"] == "File:DC generator.png"
    assert results[0]["artist"] == "Alex"
    assert results[0]["license"] == "CC BY-SA 4.0"
    assert results[0]["source_url"].startswith("https://commons.wikimedia.org/")
    get.assert_called_once()
    response.raise_for_status.assert_called_once()


def test_search_requires_a_query():
    with pytest.raises(ValueError, match="Enter a topic"):
        search_wikimedia_images("   ")


def test_search_skips_untrusted_image_urls():
    response = Mock()
    response.json.return_value = {
        "query": {
            "pages": {
                "1": {
                    "title": "File:unexpected.png",
                    "fullurl": "https://commons.wikimedia.org/wiki/File:unexpected.png",
                    "imageinfo": [{
                        "thumburl": "https://example.com/untrusted.png",
                        "extmetadata": {},
                    }],
                }
            }
        }
    }

    with patch("report_generator.online_images.requests.get", return_value=response):
        assert search_wikimedia_images("diagram") == []


def test_download_wikimedia_image_converts_to_png_bytes():
    original = BytesIO()
    Image.new("RGB", (12, 8), color="red").save(original, format="JPEG")
    response = Mock()
    response.content = original.getvalue()

    with patch("report_generator.online_images.requests.get", return_value=response):
        image_bytes = download_wikimedia_image({
            "download_url": "https://upload.wikimedia.org/wikipedia/commons/example.jpg"
        })

    with Image.open(BytesIO(image_bytes)) as result:
        assert result.format == "PNG"
        assert result.size == (12, 8)


def test_download_rejects_untrusted_urls():
    with pytest.raises(ValueError, match="trusted Wikimedia Commons URL"):
        download_wikimedia_image({
            "download_url": "https://example.com/image.png"
        })
