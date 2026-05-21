"""
Marca de agua (Watermarking) para PDFs.
"""

import fitz
import io
import math
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Watermarker:
    """Aplica marcas de agua a PDFs."""

    @staticmethod
    def apply_text_watermark(
        doc: fitz.Document,
        text: str = "CONFIDENCIAL",
        opacity: float = 0.15,
        angle: int = 45,
        fontsize: float = 60,
        color: tuple = (0.8, 0.8, 0.8),
        pages: Optional[list] = None,
    ) -> fitz.Document:
        """
        Aplica marca de agua de texto rotada en todas las paginas.
        
        Usa write_text con matriz de rotacion para lograr el angulo.
        """
        page_indices = pages if pages is not None else range(len(doc))

        for page_idx in page_indices:
            if page_idx >= len(doc):
                continue
            page = doc[page_idx]
            rect = page.rect
            center_x = rect.width / 2
            center_y = rect.height / 2

            text_width = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
            text_x = center_x - text_width / 2
            text_y = center_y

            if angle != 0:
                rad = math.radians(angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                shape = page.new_shape()
                shape.insert_text(
                    fitz.Point(text_x, text_y),
                    text,
                    fontsize=fontsize,
                    fontname="helv",
                    color=color,
                    render_mode=0,
                    morph=(fitz.Point(center_x, center_y), fitz.Matrix(cos_a, sin_a, -sin_a, cos_a, 0, 0)),
                )
                shape.commit()
            else:
                page.insert_text(
                    fitz.Point(text_x, text_y),
                    text,
                    fontname="helv",
                    fontsize=fontsize,
                    color=color,
                    render_mode=0,
                )

            logger.info(f"Marca de agua aplicada en pagina {page_idx}")

        return doc

    @staticmethod
    def apply_stamp(
        doc: fitz.Document,
        text: str = "CENSURADO",
        page_idx: int = 0,
        x: float = 400,
        y: float = 50,
        fontsize: float = 14,
        color: tuple = (0.8, 0, 0),
    ) -> fitz.Document:
        """Aplica un sello de texto en una posicion especifica."""
        if page_idx >= len(doc):
            raise ValueError(f"Pagina {page_idx} fuera de rango")

        page = doc[page_idx]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        stamp_text = f"{text} - {timestamp}"

        text_length = fitz.get_text_length(stamp_text, fontname="helv", fontsize=fontsize)
        rect = fitz.Rect(x, y, x + text_length + 10, y + fontsize + 8)

        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=color, fill=None, width=1)
        shape.insert_text(
            fitz.Point(x + 5, y + fontsize + 2),
            stamp_text,
            fontsize=fontsize,
            fontname="helv",
            color=color,
        )
        shape.commit()

        return doc
