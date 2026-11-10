def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """固定長度 + overlap 切分文字，僅用於本地文件 ingest 路徑。"""
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    stripped = text.strip()
    if not stripped:
        return []

    if len(stripped) <= chunk_size:
        return [stripped]

    stride = chunk_size - overlap
    chunks = []
    start = 0
    while start < len(stripped):
        chunks.append(stripped[start : start + chunk_size])
        if start + chunk_size >= len(stripped):
            break
        start += stride
    return chunks
