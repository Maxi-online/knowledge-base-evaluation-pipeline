"""Documentation ingestion stages."""

from .get_articles_url import get_articles_url
from .get_articles_text import get_articles_text


def kb_update(url=None):
    get_articles_url(url)
    return get_articles_text()
