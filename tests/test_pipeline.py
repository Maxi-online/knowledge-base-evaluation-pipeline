import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from config import get_config
from demo import run_demo
from knowledge_base_supporting.get_questions import parse_questions
from knowledge_base_supporting.get_questions_similarity import find_similar_questions
from knowledge_base_supporting.get_answers import answers_from_llm
from knowledge_base_supporting.get_score import validate_scores, cluster_scores, SCORE_FIELDS
from knowledge_base_updating.get_articles_url import discover_articles
from knowledge_base_updating.get_articles_text import process_article
from knowledge_base_updating.get_chunks import split_to_chunks_md_text
from utils.storage import read_json, write_json


def scores(value=3):
    return {field: value for field in SCORE_FIELDS}


def test_english_questions_are_not_discarded():
    assert parse_questions("1. What is the retention period?\n2. Who may edit records?") == [
        "What is the retention period?",
        "Who may edit records?",
    ]
    assert parse_questions('{"questions":["What is retained?","What is retained?"]}') == [
        "What is retained?"
    ]


@pytest.mark.parametrize(
    "value",
    [
        {**scores(), "accuracy": True},
        {**scores(), "accuracy": float("nan")},
        {**scores(), "accuracy": 6},
        {**scores(), "accuracy": -1},
        {"accuracy": 3},
        [3, 3, 3, 3],
    ],
)
def test_invalid_judge_vectors_fail_closed(value):
    with pytest.raises(ValueError):
        validate_scores(value)


def test_score_fields_are_read_by_name_not_json_order():
    value = {"clarity": 1, "contextual_relevance": 2, "completeness": 3, "accuracy": 4}
    assert validate_scores(json.dumps(value)) == {
        "accuracy": 4,
        "completeness": 3,
        "clarity": 1,
        "contextual_relevance": 2,
    }


def test_cluster_count_is_validated_against_small_dataset():
    rows = [scores(1), scores(5)]
    with pytest.raises(ValueError):
        cluster_scores(rows, n_clusters=10)
    with pytest.raises(ValueError):
        cluster_scores([scores(1), scores(1)], n_clusters=2)
    frame, diagnostics = cluster_scores(rows, n_clusters=2)
    assert len(frame) == 2 and diagnostics["silhouette"] is None


def test_similarity_keeps_all_questions_and_composite_chunk_provenance():
    store = {
        "chunks": [
            {"id": "same-local-id", "article_id": name, "questions": ["Who may edit records?"]}
            for name in ("a", "b", "c")
        ]
    }
    result = find_similar_questions(store, 0.7)
    assert len(result["questions"]) == 3
    assert result["questions"][0]["similarity"] == {"questions": 2, "chunks": 2, "articles": 2}


def test_parallel_answers_stay_attached_to_their_question(tmp_path):
    config = get_config()
    config["GenQuestions"]["questions_storage"] = str(tmp_path / "questions.json")
    config["GenAnswers"]["answers_storage"] = str(tmp_path / "answers.json")
    config["GenAnswers"]["tpe_max_workers"] = "4"
    write_json(
        config["GenQuestions"]["questions_storage"],
        {
            "chunks": [
                {
                    "id": "a",
                    "article_id": "one",
                    "questions": ["Question one?", "Question two?", "Question three?"],
                }
            ]
        },
    )

    class Index:
        def similarity_search(self, query, k):
            return [
                SimpleNamespace(page_content="Evidence for " + query, metadata={"question": query})
            ]

    class Bot:
        def chat(self, prompt):
            return prompt.rsplit("Question: ", 1)[1]

    result = answers_from_llm(Index(), Bot(), config)
    assert [row["answer"] for row in result["frames"]] == [
        "Question one?",
        "Question two?",
        "Question three?",
    ]
    assert all(row["question"] == row["evidence"][0]["question"] for row in result["frames"])


def test_crawl_is_bounded_and_stays_on_the_selected_origin():
    pages = {
        "https://example.org/docs": '<a href="/article">Article</a><a href="https://outside.example.net/private">External</a>',
        "https://example.org/article": "<article><h1>Policy</h1><p>Readers can view records.</p></article>",
    }
    called = []

    def fetch(url):
        called.append(url)
        return pages[url]

    result = discover_articles("https://example.org/docs", max_pages=2, fetch=fetch)
    assert result["pages_visited"] == 2 and len(result["articles"]) == 1
    assert called == list(pages)


def test_article_extraction_retains_table_cells_and_removes_scripts():
    from bs4 import BeautifulSoup

    html = "<article><h1>Roles</h1><p>Access rules.</p><table><tr><th>Role</th><th>Right</th></tr><tr><td>Reader</td><td>View</td></tr></table><script>privateFunction()</script></article>"
    text = process_article(BeautifulSoup(html, "html.parser").article)
    assert "Reader | View" in text and "# Roles" in text and "privateFunction" not in text


def test_chunker_does_not_silently_accept_invalid_overlap():
    with pytest.raises(ValueError):
        split_to_chunks_md_text("policy", 100, 100)
    assert split_to_chunks_md_text("") == []


def test_offline_pipeline_runs_through_clustering(tmp_path):
    result = run_demo(tmp_path / "demo")
    assert result["samples"] == 6 and result["clusters"] == 3 and result["live_model_requests"] == 0
    assert (tmp_path / "demo/score-clusters.csv").is_file()
    assert len(read_json(tmp_path / "demo/answers.json")["frames"]) == 6
