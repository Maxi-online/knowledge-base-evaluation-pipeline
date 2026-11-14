"""Validate judge scores and cluster four named score dimensions."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from config import get_config
from llm_chat_bots import llm_init
from utils.storage import bot_config, parse_json_response, read_json, workers, write_json

SCORE_FIELDS = ("accuracy", "completeness", "clarity", "contextual_relevance")


def validate_scores(value):
    if isinstance(value, str):
        value = parse_json_response(value)
    if not isinstance(value, dict) or set(value) != set(SCORE_FIELDS):
        raise ValueError("Judge output must contain the four named score dimensions")
    output = {}
    for field in SCORE_FIELDS:
        score = value[field]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not np.isfinite(score)
            or not 0 <= score <= 5
        ):
            raise ValueError("Every judge score must be a finite number from zero to five")
        output[field] = float(score)
    return output


def get_score(chat_bot=None, config=None):
    config = config or get_config()
    section = config["GenScore"]
    chat_bot = chat_bot or llm_init(bot_config(section))
    frames = read_json(config["GenAnswers"]["answers_storage"])["frames"]

    def score(frame):
        prompt = json.dumps(
            {k: frame.get(k) for k in ("question", "answer", "evidence", "evidence_text")},
            ensure_ascii=False,
        )
        return {**frame, "score": validate_scores(chat_bot.chat(prompt))}

    with ThreadPoolExecutor(max_workers=workers(section)) as executor:
        result = {"frames": list(executor.map(score, frames))}
    write_json(section["score_storage"], result)
    return result


def parse_score_data(config=None):
    config = config or get_config()
    frames = read_json(config["GenScore"]["score_storage"])["frames"]
    return [
        {**{k: v for k, v in frame.items() if k != "score"}, **validate_scores(frame["score"])}
        for frame in frames
    ]


def cluster_scores(rows, n_clusters=3):
    frame = pd.DataFrame(rows)
    if len(frame) < 2 or not 1 <= n_clusters <= len(frame):
        raise ValueError(
            "Cluster count must be positive and no larger than a dataset with at least two rows"
        )
    if any(field not in frame.columns for field in SCORE_FIELDS):
        raise ValueError("Missing score dimensions")
    values = frame[list(SCORE_FIELDS)].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or (values > 5).any():
        raise ValueError("Clustering requires finite scores in the zero-to-five range")
    distinct = len(np.unique(values, axis=0))
    if n_clusters > distinct:
        raise ValueError("Cluster count exceeds the number of distinct score vectors")
    scaler = StandardScaler()
    scaled = scaler.fit_transform(values)
    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(scaled)
    frame["cluster"] = model.labels_
    labels = len(set(model.labels_))
    silhouette = float(silhouette_score(scaled, model.labels_)) if 1 < labels < len(frame) else None
    diagnostics = {
        "samples": len(frame),
        "clusters": labels,
        "random_state": 42,
        "features": list(SCORE_FIELDS),
        "standardized": True,
        "silhouette": silhouette,
        "centers_original_scale": scaler.inverse_transform(model.cluster_centers_).tolist(),
        "interpretation": "Clusters summarize judge scores; they do not establish answer correctness.",
    }
    return frame, diagnostics


def clustering_and_save(rows, config=None):
    config = config or get_config()
    section = config["GenScore"]
    frame, diagnostics = cluster_scores(rows, int(section["clusters"]))
    path = Path(section["score_stats_storage"])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    write_json(path.with_suffix(".diagnostics.json"), diagnostics)
    return diagnostics


def process_score():
    get_score()
    return clustering_and_save(parse_score_data())
