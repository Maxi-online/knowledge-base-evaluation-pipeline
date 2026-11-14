"""Split documents with explicit size and overlap validation."""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_to_chunks_md_text(text, chunk_size=1000, chunk_overlap=100):
    chunk_size, chunk_overlap = int(chunk_size), int(chunk_overlap)
    if chunk_size < 1 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Require a positive chunk size and a smaller, nonnegative overlap")
    if not text.strip():
        return []
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n\n", "\n", " ", ""],
    ).split_text(text)
