"""Atomic UTF-8 artifact helpers shared by pipeline stages."""

import json
import os
from pathlib import Path
import tempfile


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_json_response(text):
    text = text.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == fence else text
    return json.loads(text)


def workers(section):
    count = int(section.get("tpe_max_workers", "4"))
    if not 1 <= count <= 16:
        raise ValueError("Worker count must be between 1 and 16")
    return count


def bot_config(section):
    return {
        "name": section["llm_name"],
        "model": section["model_name"],
        "system_message": Path(section["prompt_system"]).read_text(encoding="utf-8"),
    }


def chunks(knowledge):
    for article in knowledge:
        for chunk in article["content"]["chunks"]:
            text = chunk.get("text") or chunk.get("en") or chunk.get("ru")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Every knowledge chunk must contain nonempty text")
            yield article, chunk, text
