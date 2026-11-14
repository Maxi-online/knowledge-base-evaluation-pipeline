"""Retrieve evidence and answer each question with independent worker inputs."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from config import get_config
from llm_chat_bots import llm_init
from utils.storage import bot_config, chunks, read_json, workers, write_json


def create_embedding_db(config=None):
    config = config or get_config()
    knowledge = read_json(
        Path(config["KnowledgeBase"]["knowledge_base_storage"]) / "knowledge_base.json"
    )
    rows = list(chunks(knowledge))
    if not rows:
        raise ValueError("The knowledge base is empty")
    return FAISS.from_texts(
        [text for _, _, text in rows],
        OpenAIEmbeddings(model="text-embedding-3-small"),
        metadatas=[{"article_id": a["id"], "chunk_id": c["id"]} for a, c, _ in rows],
    )


def answers_from_llm(db, chat_bot=None, config=None):
    config = config or get_config()
    section = config["GenAnswers"]
    chat_bot = chat_bot or llm_init(bot_config(section))
    questions = read_json(config["GenQuestions"]["questions_storage"])
    jobs = [(chunk, q) for chunk in questions["chunks"] for q in chunk["questions"]]

    def answer(job):
        chunk, question = job
        docs = db.similarity_search(question, k=int(section["similarity_search_neighbours"]))
        context = "\n\n".join(doc.page_content for doc in docs)
        response = chat_bot.chat("Evidence:\n" + context + "\n\nQuestion: " + question)
        return {
            "article_id": chunk["article_id"],
            "chunk_id": chunk["id"],
            "question": question,
            "answer": response,
            "evidence": [dict(doc.metadata) for doc in docs],
            "evidence_text": context,
        }

    with ThreadPoolExecutor(max_workers=workers(section)) as executor:
        result = {"frames": list(executor.map(answer, jobs))}
    write_json(section["answers_storage"], result)
    return result


def process_answers():
    return answers_from_llm(create_embedding_db())
