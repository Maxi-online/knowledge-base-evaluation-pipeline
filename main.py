"""Command-line entry point for explicit and resumable pipeline stages."""

import argparse
import json
from config.settings import configure_logging


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base Evaluation Pipeline")
    parser.add_argument(
        "stage",
        choices=["ingest", "questions", "similarity", "answers", "score", "cluster", "run", "demo"],
    )
    parser.add_argument("--url", help="Explicit documentation URL for ingestion")
    parser.add_argument(
        "--output", default="var/demo", help="Output directory for the offline demo"
    )
    args = parser.parse_args()
    configure_logging()
    if args.stage == "demo":
        from demo import run_demo

        result = run_demo(args.output)
    else:
        from knowledge_base_updating import kb_update
        from knowledge_base_supporting.get_questions import process_questions
        from knowledge_base_supporting.get_questions_similarity import process_similarity
        from knowledge_base_supporting.get_answers import process_answers
        from knowledge_base_supporting.get_score import (
            get_score,
            parse_score_data,
            clustering_and_save,
        )

        if args.stage == "ingest":
            if not args.url:
                parser.error("ingest requires --url")
            result = kb_update(args.url)
        elif args.stage == "questions":
            result = process_questions()
        elif args.stage == "similarity":
            result = process_similarity()
        elif args.stage == "answers":
            result = process_answers()
        elif args.stage == "score":
            result = get_score()
        elif args.stage == "cluster":
            result = clustering_and_save(parse_score_data())
        else:
            if args.url:
                kb_update(args.url)
            process_questions()
            process_similarity()
            process_answers()
            get_score()
            result = clustering_and_save(parse_score_data())
    print(
        json.dumps(
            {
                "stage": args.stage,
                "result": result if args.stage in {"demo", "cluster"} else "completed",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
