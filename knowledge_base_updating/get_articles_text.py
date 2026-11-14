"""Extract article content, preserving headings, lists and tables."""

import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
from config import get_config
from utils.storage import read_json, write_json
from .get_articles_url import get_html
from .get_chunks import split_to_chunks_md_text


def process_article(article):
    document = BeautifulSoup(str(article), "html.parser")
    for tag in document(["script", "style", "nav", "form"]):
        tag.decompose()
    parts = []
    for element in document.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
        if element.find_parent(["table", "li"]) is not None:
            continue
        if element.name == "table":
            for row in element.find_all("tr"):
                parts.append(
                    " | ".join(c.get_text(" ", strip=True) for c in row.find_all(["th", "td"]))
                )
        elif element.name.startswith("h"):
            parts.append("#" * int(element.name[1]) + " " + element.get_text(" ", strip=True))
        elif element.name == "li":
            parts.append("- " + element.get_text(" ", strip=True))
        else:
            parts.append(element.get_text(" ", strip=True))
    return "\n\n".join(p for p in parts if p.strip())


def get_articles_text(config=None, fetch=get_html):
    config = config or get_config()
    section = config["KnowledgeBase"]
    cache = read_json(section["cache"])
    articles = []
    for item in cache["articles"]:
        soup = BeautifulSoup(fetch(item["url"]), "html.parser")
        article = soup.select_one(section.get("article_selector", "article"))
        if article is None:
            raise ValueError("An expected article element was not found")
        text = process_article(article)
        pieces = split_to_chunks_md_text(text, section["chunk_size"], section["chunk_overlap"])
        if not pieces:
            raise ValueError("An article contained no usable text")
        chunks = [
            {
                "id": hashlib.sha256(
                    (item["id"] + ":" + str(i) + ":" + piece).encode()
                ).hexdigest()[:16],
                "text": piece,
            }
            for i, piece in enumerate(pieces)
        ]
        articles.append(
            {
                "id": item["id"],
                "title": item["title"],
                "url": item["url"],
                "content": {"chunks": chunks},
            }
        )
    write_json(Path(section["knowledge_base_storage"]) / "knowledge_base.json", articles)
    return articles
