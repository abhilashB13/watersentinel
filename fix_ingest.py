import pathlib

p = pathlib.Path('rag/ingest.py')
code = p.read_text(encoding='utf-8')

old_block = """def get_embeddings(texts: list[str]) -> list[list[float]]:
    \"\"\"
    Generate embeddings using Google text-embedding-004.
    Processes in batches to avoid API rate limits.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (each a list of floats)
    \"\"\"
    embeddings = []
    batch_size = 10  # Google API limit per request

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch,
                task_type="RETRIEVAL_DOCUMENT",  # Optimised for document storage
            )
            embeddings.extend(result["embedding"])"""

new_block = """def get_embeddings(texts: list[str]) -> list[list[float]]:
    embeddings = []
    batch_size = 10
    client = genai.Client()

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
            )
            embeddings.extend([item.values for item in result.embeddings])"""

if old_block in code:
    code = code.replace(old_block, new_block)
    p.write_text(code, encoding='utf-8')
    print("? Successfully patched rag/ingest.py!")
else:
    # Try a loose fallback swap if whitespaces match slightly differently
    code = code.replace('genai.embed_content', 'genai.Client().models.embed_content')
    code = code.replace('content=batch', 'contents=batch')
    code = code.replace('result["embedding"]', '[item.values for item in result.embeddings]')
    p.write_text(code, encoding='utf-8')
    print("?? Applied fallback replacements.")
