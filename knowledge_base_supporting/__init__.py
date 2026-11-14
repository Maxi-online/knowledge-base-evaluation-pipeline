"""Question, retrieval, judge and clustering stages."""


def kb_support():
    from .get_questions import process_questions
    from .get_questions_similarity import process_similarity
    from .get_answers import process_answers
    from .get_score import process_score

    process_questions()
    process_similarity()
    process_answers()
    return process_score()
