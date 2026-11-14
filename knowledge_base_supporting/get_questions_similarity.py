"""Near-duplicate question review using TF-IDF cosine similarity."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import get_config
from utils.storage import read_json, write_json


def find_similar_questions(question_store, threshold=0.7):
    if not 0 <= threshold <= 1:
        raise ValueError("Similarity threshold must be between zero and one")
    flat = [
        {"question": q, "chunk_id": chunk["id"], "article_id": chunk["article_id"]}
        for chunk in question_store["chunks"]
        for q in chunk["questions"]
    ]
    if not flat:
        return {"questions": [], "threshold": threshold}
    try:
        matrix = TfidfVectorizer().fit_transform([r["question"] for r in flat])
        similarity = cosine_similarity(matrix)
    except ValueError as error:
        raise ValueError("Questions contain no usable TF-IDF vocabulary") from error
    output = []
    for index, row in enumerate(flat):
        neighbours = [
            {**other, "score": float(similarity[index, j])}
            for j, other in enumerate(flat)
            if j != index and similarity[index, j] > threshold
        ]
        output.append(
            {
                **row,
                "similar_questions": neighbours,
                "similarity": {
                    "questions": len(neighbours),
                    "chunks": len({(n["article_id"], n["chunk_id"]) for n in neighbours}),
                    "articles": len({n["article_id"] for n in neighbours}),
                },
            }
        )
    return {"questions": output, "threshold": threshold}


def process_similarity(config=None):
    config = config or get_config()
    section = config["GenQuestionsSimilarity"]
    result = find_similar_questions(
        read_json(config["GenQuestions"]["questions_storage"]),
        float(section["similarity_search_threshold"]),
    )
    write_json(section["similarity_storage"], result)
    return result
