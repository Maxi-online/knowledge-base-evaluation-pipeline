"""Bounded, same-origin documentation discovery from an explicit source URL."""

from collections import deque
import hashlib
from urllib.parse import urldefrag, urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from config import get_config
from utils.storage import write_json


def get_html(url):
    response = requests.get(
        url,
        timeout=(10, 30),
        allow_redirects=False,
        headers={"User-Agent": "KnowledgeBaseEvaluation/1.0"},
    )
    if 300 <= response.status_code < 400:
        raise ValueError("Use the final documentation URL; automatic redirects are disabled")
    response.raise_for_status()
    if "text/html" not in response.headers.get("Content-Type", "text/html"):
        raise ValueError("Expected an HTML documentation page")
    if len(response.content) > 5_000_000:
        raise ValueError("Documentation page exceeds the five-megabyte limit")
    return response.text


def discover_articles(start_url, max_pages=30, fetch=get_html):
    origin = urlparse(start_url)
    if (
        origin.scheme not in {"https", "http"}
        or not origin.netloc
        or origin.username
        or origin.password
    ):
        raise ValueError("Supply an HTTP(S) documentation URL without embedded credentials")
    if not 1 <= max_pages <= 1000:
        raise ValueError("max_pages must be between one and one thousand")
    pending = deque([urldefrag(start_url)[0]])
    seen = set()
    articles = []
    while pending and len(seen) < max_pages:
        url = pending.popleft()
        if url in seen:
            continue
        seen.add(url)
        soup = BeautifulSoup(fetch(url), "html.parser")
        if soup.find("article"):
            title = soup.find("h1") or soup.find("title")
            articles.append(
                {
                    "id": hashlib.sha256(url.encode()).hexdigest()[:16],
                    "title": title.get_text(" ", strip=True) if title else urlparse(url).path,
                    "url": url,
                }
            )
        for link in soup.find_all("a", href=True):
            target = urldefrag(urljoin(url, link["href"]))[0]
            parsed = urlparse(target)
            if (
                (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc)
                and not parsed.username
                and target not in seen
            ):
                pending.append(target)
    return {"articles": articles, "pages_visited": len(seen), "max_pages": max_pages}


def get_articles_url(start_url=None, config=None):
    config = config or get_config()
    section = config["KnowledgeBase"]
    url = start_url or section.get("knowledge_base_url")
    if not url:
        raise ValueError("An explicit documentation URL is required for ingestion")
    result = discover_articles(url, int(section["max_pages"]))
    if not result["articles"]:
        raise ValueError("No article elements were found in the bounded crawl")
    write_json(section["cache"], result)
    return result
