"""Offline integration example with explicit deterministic generator/judge stubs."""

import json
from pathlib import Path
from langchain_core.documents import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config.settings import ROOT
from config import get_config
from utils.storage import chunks, read_json, write_json
from knowledge_base_supporting.get_questions import questions_from_llm
from knowledge_base_supporting.get_questions_similarity import process_similarity
from knowledge_base_supporting.get_answers import answers_from_llm
from knowledge_base_supporting.get_score import get_score, parse_score_data, clustering_and_save


class LexicalDemoIndex:
    def __init__(self, knowledge):
        self.rows = list(chunks(knowledge))
        self.vectorizer = TfidfVectorizer()
        self.matrix = self.vectorizer.fit_transform([text for _, _, text in self.rows])

    def similarity_search(self, query, k=3):
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        output = []
        for i in scores.argsort()[::-1][:k]:
            article, chunk, text = self.rows[i]
            output.append(
                Document(
                    page_content=text,
                    metadata={"article_id": article["id"], "chunk_id": chunk["id"]},
                )
            )
        return output


class DemoQuestionGenerator:
    def chat(self, text):
        topic = next(
            (
                word
                for word in ["retention", "reader", "backup", "API", "audit", "support"]
                if word.lower() in text.lower()
            ),
            "workspace",
        )
        return json.dumps({"questions": ["What does the " + topic + " policy require?"]})


class DemoAnswerGenerator:
    def chat(self, text):
        return (
            "Synthetic adapter answer. "
            + text.split("Evidence:\n", 1)[-1].split("\n\nQuestion:", 1)[0][:160]
        )


class DemoJudge:
    def chat(self, text):
        question = json.loads(text)["question"]
        values = (
            [1, 1, 2, 1]
            if "retention" in question or "reader" in question
            else [3, 3, 3, 3]
            if "backup" in question or "API" in question
            else [5, 4, 5, 5]
        )
        return json.dumps(
            dict(zip(("accuracy", "completeness", "clarity", "contextual_relevance"), values))
        )


def run_demo(output):
    config = get_config()
    output = Path(output).resolve()
    for section in config.values():
        if "tpe_max_workers" in section:
            section["tpe_max_workers"] = "1"
    config["KnowledgeBase"]["knowledge_base_storage"] = str(output / "knowledge")
    for section, key, name in [
        ("GenQuestions", "questions_storage", "questions.json"),
        ("GenQuestionsSimilarity", "similarity_storage", "similarity.json"),
        ("GenAnswers", "answers_storage", "answers.json"),
        ("GenScore", "score_storage", "scores.json"),
        ("GenScore", "score_stats_storage", "score-clusters.csv"),
    ]:
        config[section][key] = str(output / name)
    knowledge = read_json(ROOT / "examples/knowledge_base.json")
    write_json(output / "knowledge/knowledge_base.json", knowledge)
    questions_from_llm(DemoQuestionGenerator(), config)
    process_similarity(config)
    answers_from_llm(LexicalDemoIndex(knowledge), DemoAnswerGenerator(), config)
    get_score(DemoJudge(), config)
    result = clustering_and_save(parse_score_data(config), config)
    result.update(mode="offline synthetic integration example", live_model_requests=0)
    write_json(output / "demo-report.json", result)
    return result
