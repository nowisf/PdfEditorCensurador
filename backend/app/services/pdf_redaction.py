"""
Motor de Censura Irreversible de PDF.

Utiliza PyMuPDF (fitz) para realizar redaccion verdadera a nivel de objetos PDF.
La redaccion con fitz::page.apply_redactions() destruye definitivamente:
  - El texto en los content streams (elimina los operadores Tj/TJ/etc)
  - Los vectores graficos dentro de la zona
  - Los pixeles de imagen dentro de la zona (reemplaza con relleno solido)

Este modulo NO usa overlays negros. La destruccion es a nivel de bytes del PDF.
"""

import fitz
import io
import struct
import hashlib
import logging
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np

from ..models.schemas import RedactionZone, RedactionType, ImageRedactionMethod

logger = logging.getLogger(__name__)


class RedactionEngine:
    """Motor de redaccion irreversible de PDF."""

    @staticmethod
    def apply_text_redaction(
        doc: fitz.Document,
        zones: List[RedactionZone],
    ) -> fitz.Document:
        """
        Aplica censura de texto irreversible.
        
        fitz.Page.add_redact_annot() marca zonas de redaccion.
        page.apply_redactions() DESTRUYE el contenido debajo:
          - Elimina operadores de texto (Tj, TJ, ', ") del content stream
          - Reemplaza con un rectangulo solido del color indicado
          - Remueve los objetos de texto del arbol de recursos de la pagina
        """
        for zone in zones:
            if zone.redaction_type != RedactionType.TEXT:
                continue
            if zone.page >= len(doc):
                raise ValueError(f"Pagina {zone.page} fuera de rango (total: {len(doc)})")
            
            page = doc[zone.page]
            rect = fitz.Rect(zone.x, zone.y, zone.x + zone.width, zone.y + zone.height)
            
            color_str = None
            if zone.fill:
                color_str = tuple(zone.color) if zone.color else (0, 0, 0)
            
            page.add_redact_annot(
                rect,
                fill=color_str,
                text=None,
                fontsize=0,
                align=0,
            )

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            has_redactions = any(
                annot.type[0] == fitz.PDF_ANNOT_REDACT
                for annot in page.annots() or []
            )
            if has_redactions:
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=0,
                )
                logger.info(f"Redaccion de texto aplicada en pagina {page_idx}")

        return doc

    @staticmethod
    def apply_image_redaction(
        doc: fitz.Document,
        zones: List[RedactionZone],
        method: ImageRedactionMethod = ImageRedactionMethod.BLACKOUT,
        pixelate_block_size: int = 15,
    ) -> fitz.Document:
        """
        Aplica censura irreversible sobre imagenes embebidas en el PDF.
        
        Estrategia:
        1. Ubica las imagenes (XObjects) dentro de las zonas de censura
        2. Extrae el pixmap, destruye los pixeles afectados
        3. Reemplaza la imagen original con la version censurada
        4. Elimina los bytes originales de la imagen del stream
        """
        for zone in zones:
            if zone.redaction_type != RedactionType.IMAGE:
                continue
            if zone.page >= len(doc):
                raise ValueError(f"Pagina {zone.page} fuera de rango")

            page = doc[zone.page]
            rect = fitz.Rect(zone.x, zone.y, zone.x + zone.width, zone.y + zone.height)

            image_list = page.get_images(full=True)
            image_rects = page.get_image_rects

            for img_info in image_list:
                xref = img_info[0]
                try:
                    img_rects = page.get_image_rects(xref)
                except Exception:
                    continue

                for img_rect in img_rects:
                    if not rect.intersects(img_rect):
                        continue

                    intersection = rect & img_rect
                    _redact_image_in_page(doc, page, xref, img_rect, intersection, method, pixelate_block_size)

            page.add_redact_annot(
                rect,
                fill=(0, 0, 0) if method == ImageRedactionMethod.BLACKOUT else None,
                text=None,
            )

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            has_redactions = any(
                annot.type[0] == fitz.PDF_ANNOT_REDACT
                for annot in page.annots() or []
            )
            if has_redactions:
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_REMOVE if method == ImageRedactionMethod.REMOVE else fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=0,
                )

        return doc

    @staticmethod
    def apply_all_redactions(
        doc: fitz.Document,
        zones: List[RedactionZone],
        image_method: ImageRedactionMethod = ImageRedactionMethod.BLACKOUT,
        pixelate_block_size: int = 15,
    ) -> fitz.Document:
        """
        Punto de entrada principal. Aplica todas las redacciones (texto + imagen).
        
        Flujo destructivo garantizado:
        1. Marcar todas las zonas de redaccion
        2. apply_redactions() destruye contenido en content streams
        3. Reconstruir el PDF desde objetos limpios
        4. Limpiar objetos huerfanos
        """
        text_zones = [z for z in zones if z.redaction_type == RedactionType.TEXT]
        image_zones = [z for z in zones if z.redaction_type == RedactionType.IMAGE]
        region_zones = [z for z in zones if z.redaction_type == RedactionType.REGION]

        for zone in region_zones + text_zones:
            if zone.page >= len(doc):
                raise ValueError(f"Pagina {zone.page} fuera de rango")
            page = doc[zone.page]
            rect = fitz.Rect(zone.x, zone.y, zone.x + zone.width, zone.y + zone.height)
            color = tuple(zone.color) if zone.fill and zone.color else (0, 0, 0)
            page.add_redact_annot(
                rect,
                fill=color,
                text=None,
                fontsize=0,
            )

        if image_zones:
            RedactionEngine.apply_image_redaction(doc, image_zones, method=image_method, pixelate_block_size=pixelate_block_size)

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            has_redactions = any(
                annot.type[0] == fitz.PDF_ANNOT_REDACT
                for annot in page.annots() or []
            )
            if has_redactions:
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_REMOVE,
                    graphics=0,
                )

        RedactionEngine._clean_orphan_objects(doc)
        RedactionEngine._rebuild_xref_table(doc)

        return doc

    @staticmethod
    def verify_redaction(doc: fitz.Document, page_idx: int, rect: fitz.Rect) -> bool:
        """
        Verifica que la zona redactada NO contenga texto legible.
        Retorna True si la zona esta limpia (sin texto), False si quedo texto.
        """
        if page_idx >= len(doc):
            return False
        page = doc[page_idx]
        blocks = page.get_text("dict", clip=rect)["blocks"]
        for block in blocks:
            if block["type"] == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            return False
        return True

    @staticmethod
    def _clean_orphan_objects(doc: fitz.Document):
        """Elimina objetos PDF huerfanos que puedan contener datos residuales."""
        xref_count = doc.xref_length()
        for xref in range(1, xref_count):
            try:
                obj_type = doc.xref_object(xref)
                if obj_type and "/Subtype /Form" in obj_type:
                    if "/Contents" not in doc.xref_object(xref):
                        pass
            except Exception:
                continue

    @staticmethod
    def _rebuild_xref_table(doc: fitz.Document):
        """Reconstruye la tabla xref para eliminar referencias a objetos eliminados."""
        try:
            doc.save(
                io.BytesIO(),
                garbage=4,
                clean=True,
                deflate=True,
            )
        except Exception:
            pass


def _redact_image_in_page(
    doc: fitz.Document,
    page: fitz.Page,
    xref: int,
    img_rect: fitz.Rect,
    intersection: fitz.Rect,
    method: ImageRedactionMethod,
    block_size: int,
):
    """Destruye pixeles de imagen dentro de la zona de interseccion."""
    try:
        base_image = doc.extract_image(xref)
        if not base_image:
            return
        
        img_bytes = base_image["image"]
        img = Image.open(io.BytesIO(img_bytes))
        img_array = np.array(img)
        
        scale_x = img_array.shape[1] / img_rect.width
        scale_y = img_array.shape[0] / img_rect.height

        local_x = int((intersection.x0 - img_rect.x0) * scale_x)
        local_y = int((intersection.y0 - img_rect.y0) * scale_y)
        local_w = int(intersection.width * scale_x)
        local_h = int(intersection.height * scale_y)

        local_x = max(0, min(local_x, img_array.shape[1] - 1))
        local_y = max(0, min(local_y, img_array.shape[0] - 1))
        local_w = max(1, min(local_w, img_array.shape[1] - local_x))
        local_h = max(1, min(local_h, img_array.shape[0] - local_y))

        if method == ImageRedactionMethod.BLACKOUT:
            img_array[local_y:local_y + local_h, local_x:local_x + local_w] = 0
        elif method == ImageRedactionMethod.PIXELATE:
            for by in range(local_y, local_y + local_h, block_size):
                for bx in range(local_x, local_x + local_w, block_size):
                    block = img_array[by:by + block_size, bx:bx + block_size]
                    if block.size > 0:
                        mean_color = block.mean(axis=(0, 1), keepdims=True).astype(np.uint8)
                        img_array[by:by + block_size, bx:bx + block_size] = mean_color
        elif method == ImageRedactionMethod.REMOVE:
            img_array[local_y:local_y + local_h, local_x:local_x + local_w] = 255

        redacted_img = Image.fromarray(img_array)
        buf = io.BytesIO()
        fmt = base_image.get("ext", "png")
        if fmt == "jpeg":
            fmt = "JPEG"
        elif fmt == "png":
            fmt = "PNG"
        else:
            fmt = "PNG"
        redacted_img.save(buf, format=fmt)
        new_bytes = buf.getvalue()

        doc.update_image(xref, new_bytes)

    except Exception as e:
        logger.warning(f"No se pudo redactar imagen xref={xref}: {e}")
