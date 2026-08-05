import pymupdf

# Chroma Cloud limits each record's document payload to 16 KiB (16384 bytes).
# We chunk well under this limit to leave headroom for the embedded source text.
MAX_CHUNK_BYTES = 16000
DEFAULT_OVERLAP_LINES = 2


def extract_text_from_pdf(file_stream: bytes) -> tuple[str, int]:
    document = pymupdf.open(stream=file_stream, filetype="pdf")

    all_text = ""
    for page in document:
        all_text += page.get_text()

    page_count = len(document)
    document.close()

    return all_text, page_count


def _split_long_line(line: str, max_bytes: int) -> list[str]:
    """Break a single line that exceeds max_bytes into smaller word-based pieces."""
    if len(line.encode("utf-8")) + 1 <= max_bytes:
        return [line]

    pieces = []
    current = ""
    for word in line.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate.encode("utf-8")) + 1 > max_bytes:
            if current:
                pieces.append(current)
                current = ""
            # A single word can itself exceed max_bytes; slice it by bytes.
            pieces.extend(_split_by_bytes(word, max_bytes))
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _split_by_bytes(text: str, max_bytes: int) -> list[str]:
    """Slice a long token into pieces of, at most, max_bytes bytes."""
    pieces = []
    current = ""
    current_bytes = 0
    for char in text:
        char_bytes = len(char.encode("utf-8"))
        if current_bytes + char_bytes > max_bytes:
            pieces.append(current)
            current = char
            current_bytes = char_bytes
        else:
            current += char
            current_bytes += char_bytes
    if current:
        pieces.append(current)
    return pieces


def chunk_text(
    text: str,
    max_bytes: int = MAX_CHUNK_BYTES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
) -> list[dict]:
    """Line-based chunking respecting Chroma Cloud's 16 KiB document limit.

    Lines are accumulated into chunks of, at most, ``max_bytes`` bytes. Chunks
    that would otherwise fall on a sequence boundary carry an overlap of the
    previous chunk's trailing lines to preserve context across splits.

    Returns a list of ``{"index": int, "text": str}`` payloads.
    """
    if not text:
        return []

    chunks = []
    buffer: list[str] = []
    buffer_bytes = 0

    def flush():
        nonlocal buffer, buffer_bytes
        if buffer:
            chunks.append({"index": len(chunks), "text": "\n".join(buffer)})

        if overlap_lines > 0:
            overlap = buffer[-overlap_lines:] if buffer else []
            buffer = list(overlap)
            buffer_bytes = sum(len(line.encode("utf-8")) + 1 for line in overlap)
        else:
            buffer = []
            buffer_bytes = 0

    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\r")
        for piece in _split_long_line(line, max_bytes):
            piece_bytes = len(piece.encode("utf-8")) + 1  # +1 for the newline
            if buffer and buffer_bytes + piece_bytes > max_bytes:
                flush()
            buffer.append(piece)
            buffer_bytes += piece_bytes

    flush()
    return chunks