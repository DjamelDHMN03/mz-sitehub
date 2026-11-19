"""
Tests du service RAG — utilisent un vrai PDF (généré via reportlab dans le
test lui-même, pour ne dépendre d'aucun fichier externe) et pypdf pour
l'extraction, tous deux déjà nécessaires en dépendances.
"""
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from reportlab.pdfgen import canvas

from app.services.rag import (
    PdfExtractionError,
    PageText,
    TextChunk,
    chunk_pages,
    cosine_similarity,
    extract_pages,
    rank_chunks_by_similarity,
)


def _make_test_pdf(text: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, text)
    c.save()
    return buf.getvalue()


def test_extract_pages_real_pdf():
    pdf_bytes = _make_test_pdf("Contrat AL6328 EPIC EGUVA")
    pages = extract_pages(pdf_bytes)
    assert len(pages) == 1
    assert "AL6328" in pages[0].text


def test_chunking_produces_multiple_chunks_for_long_text():
    long_text = "Phrase de test numéro un. " * 100
    pages = [PageText(page_number=1, text=long_text)]
    chunks = chunk_pages(pages, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(c.page_number == 1 for c in chunks)


def test_chunking_empty_page_no_crash():
    pages = [PageText(page_number=2, text="")]
    assert chunk_pages(pages) == []


def test_invalid_pdf_raises_clear_error():
    with pytest.raises(PdfExtractionError):
        extract_pages(b"ceci n'est pas un PDF")


def test_cosine_similarity_identical_and_orthogonal():
    assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9
    assert abs(cosine_similarity([1, 0, 0], [0, 1, 0])) < 1e-9


def test_ranking_returns_most_relevant_first():
    chunk_a = TextChunk(content="Le contrat AL6328 est en négociation.", page_number=1, chunk_index=0)
    chunk_b = TextChunk(content="La météo à Alger est ensoleillée.", page_number=2, chunk_index=1)
    query = [1.0, 0.0, 0.0]
    candidates = [(chunk_a, [0.95, 0.1, 0.0]), (chunk_b, [0.05, 0.9, 0.2])]
    ranked = rank_chunks_by_similarity(query, candidates, top_k=2)
    assert ranked[0].chunk is chunk_a
    assert ranked[0].score > ranked[1].score
