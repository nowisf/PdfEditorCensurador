"""
Gestion de paginas de PDF.

Rotar, eliminar, reordenar, insertar paginas.
"""

import fitz
import io
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class PageManager:
    """Gestor de paginas de PDF."""

    @staticmethod
    def rotate_pages(doc: fitz.Document, page_indices: List[int], degrees: int = 90) -> fitz.Document:
        for idx in page_indices:
            if idx < len(doc):
                doc[idx].set_rotation(degrees)
        return doc

    @staticmethod
    def delete_pages(doc: fitz.Document, page_indices: List[int]) -> fitz.Document:
        for idx in sorted(page_indices, reverse=True):
            if idx < len(doc):
                doc.delete_page(idx)
        return doc

    @staticmethod
    def reorder_pages(doc: fitz.Document, new_order: List[int]) -> fitz.Document:
        new_doc = fitz.open()
        for idx in new_order:
            if idx < len(doc):
                new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        return new_doc

    @staticmethod
    def duplicate_page(doc: fitz.Document, page_idx: int) -> fitz.Document:
        if page_idx >= len(doc):
            raise ValueError(f"Pagina {page_idx} fuera de rango")
        new_doc = fitz.open()
        new_doc.insert_pdf(doc)
        new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
        return new_doc

    @staticmethod
    def extract_page(doc: fitz.Document, page_idx: int) -> bytes:
        if page_idx >= len(doc):
            raise ValueError(f"Pagina {page_idx} fuera de rango")
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
        buf = io.BytesIO()
        new_doc.save(buf, garbage=4, deflate=True)
        new_doc.close()
        return buf.getvalue()
