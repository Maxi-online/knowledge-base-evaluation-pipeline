"""Generate grounded questions with source provenance and stable order."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
from config import get_config
from llm_chat_bots import llm_init
from utils.storage import bot_config, chunks, parse_json_response, read_json, workers, write_json


def process_and_filter_line(line):
    return re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", line).strip()


def parse_questions(response):
    try:
        value = parse_json_response(response)
        values = value.get("questions", []) if isinstance(value, dict) else value
    except ValueError:
        values = [process_and_filter_line(line) for line in response.splitlines() if "?" in line]
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(v, str) or not v.strip() for v in values)
    ):
        raise ValueError("Expected a nonempty list of question strings")
    return list(dict.fromkeys(v.strip() for v in values))


def questions_from_llm(chat_bot=None, config=None):
    config = config or get_config()
    section = config["GenQuestions"]
    knowledge = read_json(
        Path(config["KnowledgeBase"]["knowledge_base_storage"]) / "knowledge_base.json"
    )
    jobs = list(chunks(knowledge))
    if not jobs:
        raise ValueError("The knowledge base contains no chunks")
    chat_bot = chat_bot or llm_init(bot_config(section))

    def generate(job):
        article, chunk, text = job
        return {
            "id": chunk["id"],
            "article_id": article["id"],
            "questions": parse_questions(chat_bot.chat(text)),
        }

    with ThreadPoolExecutor(max_workers=workers(section)) as executor:
        rows = list(executor.map(generate, jobs))
    result = {
        "total_chunks": len(rows),
        "total_questions": sum(len(r["questions"]) for r in rows),
        "chunks": rows,
    }
    write_json(section["questions_storage"], result)
    return result


def process_questions():
    return questions_from_llm()
