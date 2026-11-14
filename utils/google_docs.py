"""Explicit Google Docs text export loader."""

import re
from urllib.parse import urlparse
import requests


def download_document_text(url):
    parsed = urlparse(url)
    match = re.fullmatch(r"/document/d/([A-Za-z0-9_-]+)(?:/.*)?", parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "docs.google.com" or not match:
        raise ValueError("Expected a Google Docs HTTPS document URL")
    response = requests.get(
        "https://docs.google.com/document/d/" + match.group(1) + "/export?format=txt",
        timeout=(10, 30),
    )
    response.raise_for_status()
    return response.text
