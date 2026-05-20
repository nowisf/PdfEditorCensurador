"""
Modulo de conversion de formatos a/desde PDF.

Soporta:
- Imagenes (PNG, JPEG, TIFF, BMP) -> PDF
- PDF -> Imagenes (PNG)
- Conversion basica Word/Excel -> PDF (requiere LibreOffice en el sistema)
"""

import fitz
import io
import os
import tempfile
import logging
from PIL import Image
from typing import Optional, List

logger = logging.getLogger(__name__)


class PDFConverter:
    """Convertidor de formatos a/desde PDF."""

    @staticmethod
    def images_to_pdf(image_paths: List[str], output_path: str) -> str:
        """Convierte una o mas imagenes a un PDF."""
        doc = fitz.open()

        for img_path in image_paths:
            if not os.path.exists(img_path):
                logger.warning(f"Imagen no encontrada: {img_path}")
                continue

            img = Image.open(img_path)
            width, height = img.size

            page = doc.new_page(width=width, height=height)
            rect = fitz.Rect(0, 0, width, height)
            page.insert_image(rect, filename=img_path)

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return output_path

    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200, fmt: str = "png") -> List[str]:
        """Convierte cada pagina de un PDF a imagen."""
        doc = fitz.open(pdf_path)
        output_paths = []

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=mat)

            out_path = os.path.join(output_dir, f"page_{page_idx + 1}.{fmt}")
            pix.save(out_path)
            output_paths.append(out_path)

        doc.close()
        return output_paths

    @staticmethod
    def merge_pdfs(pdf_paths: List[str], output_path: str) -> str:
        """Combina multiples PDFs en uno solo."""
        result = fitz.open()

        for pdf_path in pdf_paths:
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF no encontrado: {pdf_path}")
                continue
            src = fitz.open(pdf_path)
            result.insert_pdf(src)
            src.close()

        result.save(output_path, garbage=4, deflate=True)
        result.close()
        return output_path

    @staticmethod
    def create_pdf_from_text(
        text: str,
        output_path: str,
        font_size: float = 12,
        margin: float = 72,
        page_size: tuple = (612, 792),
    ) -> str:
        """Crea un PDF desde texto plano."""
        doc = fitz.open()
        width, height = page_size

        page = doc.new_page(width=width, height=height)
        text_rect = fitz.Rect(margin, margin, width - margin, height - margin)

        page.insert_textbox(
            text_rect,
            text,
            fontsize=font_size,
            fontname="helv",
            color=(0, 0, 0),
        )

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return output_path

    @staticmethod
    def rotate_pages(pdf_path: str, output_path: str, degrees: int = 90) -> str:
        """Rota todas las paginas de un PDF."""
        doc = fitz.open(pdf_path)

        for page in doc:
            page.set_rotation(degrees)

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return output_path
