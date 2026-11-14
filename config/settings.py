"""Load neutral defaults and explicit local overrides."""

import configparser
import logging
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_KEYS = {
    "cache",
    "prompt_system",
    "knowledge_base_storage",
    "questions_storage",
    "similarity_storage",
    "answers_storage",
    "score_storage",
    "score_stats_storage",
}


def read_config(path=None):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ROOT / "config/default.config", encoding="utf-8")
    override = path or os.getenv("KB_CONFIG_FILE")
    if override:
        override = Path(override).expanduser().resolve()
        if not override.is_file():
            raise FileNotFoundError("The explicitly selected configuration file does not exist")
        parser.read(override, encoding="utf-8")
    result = {section: dict(parser.items(section)) for section in parser.sections()}
    for section in result.values():
        for name, value in list(section.items()):
            if name in PATH_KEYS and value:
                section[name] = str((ROOT / value).resolve())
        if "api_key" in section:
            if section["api_key"].strip():
                raise ValueError("Credentials must be supplied through the process environment")
            section["api_key"] = os.getenv("OPENAI_API_KEY", "")
        if "model_name" in section and os.getenv("OPENAI_MODEL"):
            section["model_name"] = os.environ["OPENAI_MODEL"]
    return result


def get_config():
    return read_config()


def configure_logging():
    logging.basicConfig(level=get_config()["Logging"]["level"])
