# Knowledge Base Evaluation Pipeline

A staged pipeline for **documentation ingestion, grounded question generation, question-similarity analysis, retrieved answers, evidence-aware judging and score clustering**.

The project makes the intermediate artifacts inspectable: an answer can be traced back to its question, source article, source chunk and retrieved evidence. Its classical ML components are TF-IDF similarity and KMeans clustering over four judge-score dimensions. It does not train a language model, and a cluster or judge score is not an independently verified correctness label.

This is a sanitized portfolio edition. Original customer documentation, generated Q&A, score exports, notebooks with embedded data, service settings and credentials are not distributed.

## Pipeline stages

~~~mermaid
flowchart LR
    Source[Explicit documentation URL] --> Crawl[Bounded same-origin discovery]
    Crawl --> Parse[Article extraction and chunking]
    Parse --> Questions[Grounded English questions]
    Questions --> Similarity[TF-IDF duplicate review]
    Questions --> Answers[FAISS evidence retrieval and answers]
    Answers --> Judge[Four validated judge scores]
    Judge --> Cluster[Standardization and KMeans]
    Cluster --> Output[CSV and diagnostic JSON]
~~~

Each stage has a command-line entry point. A failed generation stage raises an error rather than quietly presenting a partial output as complete. JSON artifacts are written through a temporary file and atomic replacement.

## What the implementation covers

**Ingestion.** The crawler starts only from an explicitly selected HTTP(S) documentation URL. It follows same-origin links within a configured page budget, extracts article elements and preserves headings, lists and table cells as text. Redirects are rejected so an operator supplies the final URL. Article and chunk identifiers are stable hashes of their source identities/content.

**Questions.** A bounded thread pool generates questions per source chunk. Both JSON question arrays and numbered English question lines are supported. English questions are not discarded merely because their first character is a letter. Article and chunk identifiers remain attached to each question.

**Similarity.** TF-IDF cosine similarity identifies near-duplicate questions. The output retains every question and its neighbors. It reports distinct source articles and composite article/chunk identities. Similarity is a review aid; it does not silently remove questions from the evaluation set.

**Answers.** A FAISS index built from the selected knowledge chunks retrieves evidence for each question. Each worker captures its own question and context, preventing a late-bound loop variable from attaching an answer to another question. Answer artifacts retain evidence metadata and text.

**Judging.** The judge returns accuracy, completeness, clarity and contextual_relevance. Values are read by field name, not dictionary order. Every score must be a finite number in the 0–5 range; booleans, missing dimensions, extra dimensions and out-of-range values fail validation. The judge receives the question, answer and retrieved evidence.

**Clustering.** The four dimensions are standardized before deterministic KMeans fitting with a fixed random seed and multiple initializations. Cluster count is explicit, configurable and validated against both sample count and distinct score vectors. Diagnostics include source-scale centers and silhouette when it is mathematically defined.

## Run the full offline example

~~~bash
git clone https://github.com/Maxi-online/knowledge-base-evaluation-pipeline.git
cd knowledge-base-evaluation-pipeline
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python main.py demo --output var/demo
python -m pytest -q
~~~

Windows activation:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

The example uses six fictional English source chunks. It runs question generation, similarity, answer assembly, score validation and actual KMeans clustering. Generator and judge responses are deterministic local adapters; the demo retriever is lexical TF-IDF rather than hosted embeddings.

The example needs no provider credential and makes no external requests. Its silhouette and example scores describe deliberately constructed synthetic vectors. They must not be reported as language-model accuracy, retrieval quality or production performance.

## Explicit live-stage commands

The default configuration is [config/default.config](config/default.config). It contains neutral paths and no active source URL or credential. An optional ignored local configuration can be selected through KB_CONFIG_FILE. Paths resolve relative to the repository root.

Set OPENAI_API_KEY in the process environment before intentionally using hosted generation/embedding stages. OPENAI_MODEL can override the chat-model setting. Configuration files reject a nonempty api_key value.

~~~bash
read -r -p "Documentation URL: " KB_SOURCE_URL
python main.py ingest --url "$KB_SOURCE_URL"
python main.py questions
python main.py similarity
python main.py answers
python main.py score
python main.py cluster
~~~

Supply documentation you control or are authorized to process. Ingestion has no bundled remote source. The complete no-configuration executable example is the demo command above.

python main.py run executes questions, similarity, answers, scoring and clustering against an already ingested knowledge base. Adding --url explicitly performs ingestion first. No command crawls an original customer site by default.

Live stages transmit the selected chunks, questions, answers or evidence to the configured model provider. Review that data boundary before using a private corpus. Generated artifacts belong under var/, which is excluded from Git.

## Artifacts and provenance

| Artifact | Contents |
| --- | --- |
| var/articles.json | Discovered article URLs and crawl coverage |
| var/knowledge/knowledge_base.json | Articles and stable source chunks |
| var/questions.json | Questions grouped by article/chunk |
| var/similarity.json | Question neighbors and provenance counts |
| var/answers.json | Question, answer, evidence text and evidence identifiers |
| var/scores.json | Validated score objects attached to answer frames |
| var/score-clusters.csv | Four named dimensions and cluster labels |
| var/score-clusters.diagnostics.json | Sample count, centers and clustering diagnostics |

A knowledge article contains id, title and content.chunks. Each chunk has id and text. The reader also accepts the earlier en/ru text fields for input compatibility. The published example data uses text and is entirely English.

The scoring stage preserves the answer frame before adding its validated score object. Cluster labels are arbitrary identifiers; a larger label does not imply a better answer.

## Configuration controls

| Section | Important controls |
| --- | --- |
| KnowledgeBase | Explicit source URL, max_pages, article_selector, chunk_size and chunk_overlap |
| GenQuestions | Prompt, chat model, worker count and output path |
| GenQuestionsSimilarity | Cosine threshold and output path |
| GenAnswers | Prompt, retrieval neighbors and output path |
| GenScore | Prompt, worker count, cluster count and output paths |

Worker counts are bounded. Chunk overlap must be smaller than chunk size. Clustering requires at least two rows and enough distinct score vectors. There is no automatic claim that the configured k is optimal.

## Source guide

- knowledge_base_updating/: crawl, article extraction and chunking.
- knowledge_base_supporting/get_questions.py: grounded question generation.
- knowledge_base_supporting/get_questions_similarity.py: TF-IDF similarity.
- knowledge_base_supporting/get_answers.py: evidence retrieval and parallel answer generation.
- knowledge_base_supporting/get_score.py: strict score schema and clustering.
- llm_chat_bots/: stateless model adapter; parallel jobs do not share a mutable conversation.
- utils/storage.py: artifact I/O, bounded worker configuration and JSON handling.
- examples/: synthetic source material.
- tests/: reproducible regression and integration checks.

## Evaluation limits

The current suite verifies contracts and implementation behavior: English question parsing, named score fields, malformed scores, small datasets, duplicate provenance, parallel job binding, bounded discovery, table extraction and an end-to-end offline run.

It does not establish judge calibration, human agreement, answer correctness or semantic retrieval quality. Using the same provider for generation and judging can introduce correlated errors. The four ordinal score dimensions are treated as numeric features for descriptive grouping; that assumption should be reviewed for a scientific evaluation.

A stronger study would add independently labeled questions, fixed retrieval baselines, expert scoring, disagreement analysis and sensitivity to cluster count. No such results are invented in this repository.

## License and release checks

The source is publicly visible for portfolio inspection under the restrictive [LICENSE](LICENSE), not an unrestricted open-source grant. Dependencies retain their respective licenses.

CI compiles tracked source, runs offline tests, enforces English prose, reviews configuration literals and scans reachable Git history with a pinned secret scanner. See [SECURITY.md](SECURITY.md).
