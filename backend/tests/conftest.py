import os
import sys
import tempfile
import fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.pdf_redaction import RedactionEngine
from app.services.pdf_metadata import MetadataSanitizer, sanitize_pdf_file
from app.models.schemas import RedactionZone, RedactionType, MetadataSanitizeOptions


def create_test_pdf(text: str = "Juan Perez - RUT 12.345.678-9 - Direccion: Av. Libertador 1234, Santiago") -> str:
    """Crea un PDF de prueba con texto sensible."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    text_rect = fitz.Rect(72, 72, 540, 720)
    page.insert_textbox(text_rect, text, fontsize=12, fontname="helv")
    doc.save(tmp_path)
    doc.close()
    return tmp_path


def create_test_pdf_with_image() -> str:
    """Crea un PDF de prueba con una imagen embebida."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    try:
        from PIL import Image as PILImage
        import numpy as np
        img_array = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        img = PILImage.fromarray(img_array)
        img_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(img_tmp.name)
        img_tmp.close()
        page.insert_image(fitz.Rect(50, 50, 350, 250), filename=img_tmp.name)
        os.unlink(img_tmp.name)
    except ImportError:
        pass

    page.insert_text(fitz.Point(50, 300), "Texto con imagen arriba", fontsize=12)
    doc.save(tmp_path)
    doc.close()
    return tmp_path


def create_test_pdf_with_metadata() -> str:
    """Crea un PDF con metadatos completos."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(72, 72), "Documento con metadatos", fontsize=12)

    doc.set_metadata({
        "author": "Autor Sensible",
        "creator": "Creator App v1.0",
        "producer": "Producer Tool",
        "title": "Titulo Confidencial",
        "subject": "Asunto Secreto",
        "keywords": "secreto, confidencial, privado",
        "creationDate": "D:20240101120000+03'00'",
        "modDate": "D:20240615150000+03'00'",
    })
    doc.save(tmp_path)
    doc.close()
    return tmp_path
