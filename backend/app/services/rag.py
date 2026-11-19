"""
Service RAG (sections 24, 64-65) : extraction texte -> chunking -> (embeddings
via AIProvider, non testable ici) -> recherche -> citation de sources.

Ce fichier ne dépend que de pypdf (déjà nécessaire pour lire du PDF en
Python) et de la bibliothèque standard pour tout ce qui est testable sans
LLM : extraction de texte par page, découpage en chunks avec chevauchement,
et calcul de similarité cosinus pour le classement des résultats.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class TextChunk:
    content: str
    page_number: int
    chunk_index: int


class PdfExtractionError(Exception):
    pass


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:
        raise PdfExtractionError(f"PDF illisible : {exc}") from exc

    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(PageText(page_number=i, text=text))
    return pages


def chunk_pages(
    pages: list[PageText],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    global_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(TextChunk(content=chunk_text, page_number=page.page_number, chunk_index=global_index))
                global_index += 1
            if end == len(text):
                break
            start = end - overlap

    return chunks


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Dimensions incompatibles : {len(vec_a)} vs {len(vec_b)}")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class RankedChunk:
    chunk: TextChunk
    score: float


def rank_chunks_by_similarity(
    query_embedding: list[float],
    candidates: list[tuple[TextChunk, list[float]]],
    top_k: int = 5,
) -> list[RankedChunk]:
    scored = [
        RankedChunk(chunk=chunk, score=cosine_similarity(query_embedding, emb))
        for chunk, emb in candidates
    ]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
