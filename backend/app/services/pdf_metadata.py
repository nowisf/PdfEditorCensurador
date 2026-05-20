"""
Modulo de Saneamiento Destructivo de Metadatos PDF.

Destruye TODOS los metadatos recuperables:
  - Campos estandar (Author, Creator, Producer, Title, Subject, Keywords)
  - Fechas (CreationDate, ModDate)
  - Metadatos XML/XMP embebidos
  - Miniaturas embebidas
  - Marcadores/Bookmarks (opcional)
  - Capas OC (Optional Content)
  - Informacion de PIE (Piece Info)
  - Historial de cambios (en XMP)
  - Propiedades personalizadas ocultas
"""

import fitz
import io
import re
import logging
from typing import Optional
from ..models.schemas import MetadataSanitizeOptions

logger = logging.getLogger(__name__)


class MetadataSanitizer:
    """Saneador destructivo de metadatos PDF."""

    STANDARD_FIELDS = [
        "author",
        "creator",
        "producer",
        "title",
        "subject",
        "keywords",
        "creationDate",
        "modDate",
        "trapped",
    ]

    @classmethod
    def sanitize(
        cls,
        doc: fitz.Document,
        options: Optional[MetadataSanitizeOptions] = None,
    ) -> fitz.Document:
        """
        Ejecuta el saneamiento completo y destructivo de metadatos.
        
        Este proceso es IRREVERSIBLE:
        1. Sobreescribe todos los campos de metadatos con strings vacios
        2. Elimina flujos XML/XMP completos
        3. Destruye miniaturas embebidas
        4. Limpia objetos huerfanos
        5. Reconstruye el PDF limpio
        """
        if options is None:
            options = MetadataSanitizeOptions()

        cls._overwrite_standard_metadata(doc, options)
        cls._destroy_xmp_metadata(doc)
        cls._destroy_embedded_thumbnails(doc)
        cls._destroy_piece_info(doc)
        cls._destroy_optional_content_info(doc)
        cls._clean_custom_properties(doc)
        if options.remove_bookmarks:
            cls._destroy_bookmarks(doc)
        cls._destroy_annotation_metadata(doc)
        cls._clean_incremental_updates(doc)

        logger.info("Saneamiento de metadatos completado")
        return doc

    @classmethod
    def _overwrite_standard_metadata(cls, doc: fitz.Document, options: MetadataSanitizeOptions):
        """Sobreescribe campos de metadatos estandar con valores vacios."""
        metadata = doc.metadata

        field_map = {
            "author": options.remove_author,
            "creator": options.remove_creator,
            "producer": options.remove_producer,
            "title": options.remove_title,
            "subject": options.remove_subject,
            "keywords": options.remove_keywords,
            "creationDate": options.remove_creation_date,
            "modDate": options.remove_mod_date,
        }

        clean_metadata = {}
        for field, should_remove in field_map.items():
            clean_metadata[field] = "" if should_remove else metadata.get(field, "")

        clean_metadata["format"] = metadata.get("format", "")
        clean_metadata["encryption"] = metadata.get("encryption", "")
        
        doc.set_metadata(clean_metadata)
        logger.info("Metadatos estandar sobreescritos")

    @classmethod
    def _destroy_xmp_metadata(cls, doc: fitz.Document):
        """
        Elimina DESTRUCTIVAMENTE el flujo XML/XMP del PDF.
        
        XMP puede contener historial completo de ediciones, 
        identificadores unicos, y metadatos ocultos.
        """
        xref_count = doc.xref_length()
        for xref in range(1, xref_count):
            try:
                obj_str = doc.xref_object(xref)
                if "/Type /Metadata" in obj_str or "/Subtype /XML" in obj_str:
                    stream = doc.xref_stream(xref)
                    if stream:
                        zeroed = b"\x00" * len(stream)
                        doc.update_stream(xref, zeroed)
                        doc.xref_set_key(xref, "Subtype", "null")
                        logger.info(f"Flujo XMP destruido en xref={xref}")
            except Exception:
                continue

        try:
            catalog_xref = doc.pdf_catalog()
            doc.xref_set_key(catalog_xref, "Metadata", "null")
        except Exception:
            pass

    @classmethod
    def _destroy_embedded_thumbnails(cls, doc: fitz.Document):
        """Destruye miniaturas embebidas que pueden contener datos visuales."""
        for page_idx in range(len(doc)):
            try:
                page = doc[page_idx]
                xref = page.xref
                obj_str = doc.xref_object(xref)
                if "/Thumb" in obj_str:
                    doc.xref_set_key(xref, "Thumb", "null")
                    logger.info(f"Miniatura destruida en pagina {page_idx}")
            except Exception:
                continue

    @classmethod
    def _destroy_piece_info(cls, doc: fitz.Document):
        """Elimina Piece Info que puede contener historial de edicion."""
        for page_idx in range(len(doc)):
            try:
                page = doc[page_idx]
                xref = page.xref
                obj_str = doc.xref_object(xref)
                if "/PieceInfo" in obj_str:
                    doc.xref_set_key(xref, "PieceInfo", "null")
            except Exception:
                continue

    @classmethod
    def _destroy_optional_content_info(cls, doc: fitz.Document):
        """Elimina informacion de capas opcionales (OC) que podrian ocultar datos."""
        try:
            catalog_xref = doc.pdf_catalog()
            obj_str = doc.xref_object(catalog_xref)
            if "/OCProperties" in obj_str:
                doc.xref_set_key(catalog_xref, "OCProperties", "null")
                logger.info("OCProperties destruido")
        except Exception:
            pass

    @classmethod
    def _clean_custom_properties(cls, doc: fitz.Document):
        """Elimina propiedades personalizadas ocultas en el Info dictionary."""
        try:
            info_xref = doc.doc_xref
            if info_xref > 0:
                obj_str = doc.xref_object(info_xref)
                custom_fields = re.findall(r"/(\w+)\s*\(", obj_str)
                standard_upper = [f.upper() for f in cls.STANDARD_FIELDS]
                for field in custom_fields:
                    if field.upper() not in standard_upper and field.upper() not in ["TYPE", "LENGTH", "FILTER"]:
                        doc.xref_set_key(info_xref, field, "null")
        except Exception:
            pass

    @classmethod
    def _destroy_bookmarks(cls, doc: fitz.Document):
        """Elimina marcadores que pueden revelar estructura del documento."""
        doc.set_toc([])

    @classmethod
    def _destroy_annotation_metadata(cls, doc: fitz.Document):
        """Limpia metadatos de anotaciones que puedan contener informacion del autor."""
        errors = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            annot = page.first_annot
            while annot:
                try:
                    annot.set_info(title="", content="", subject="")
                except Exception as e:
                    errors.append(f"Pagina {page_idx}: {e}")
                annot = annot.next
        if errors:
            logger.warning(f"Errores limpiando anotaciones: {errors}")

    @classmethod
    def _clean_incremental_updates(cls, doc: fitz.Document):
        """
        Elimina actualizaciones incrementales que conservan versiones anteriores.
        
        Al guardar con garbage=4 y clean=True, PyMuPDF reconstruye el PDF 
        desde cero, eliminando cualquier contenido residual de versiones previas.
        """
        pass

    @classmethod
    def get_metadata_report(cls, doc: fitz.Document) -> dict:
        """Genera un reporte de metadatos para verificacion."""
        metadata = doc.metadata
        report = {
            "standard_fields": {k: v for k, v in metadata.items() if v},
            "has_xmp": False,
            "has_thumbnails": False,
            "has_piece_info": False,
            "page_count": len(doc),
        }

        xref_count = doc.xref_length()
        for xref in range(1, xref_count):
            try:
                obj_str = doc.xref_object(xref)
                if "/Type /Metadata" in obj_str:
                    report["has_xmp"] = True
                if "/Thumb" in obj_str and "/Type /Page" in obj_str:
                    report["has_thumbnails"] = True
                if "/PieceInfo" in obj_str:
                    report["has_piece_info"] = True
            except Exception:
                continue

        return report


def sanitize_pdf_file(input_path: str, output_path: str, options: Optional[MetadataSanitizeOptions] = None) -> dict:
    """
    Funcion de conveniencia para saneamiento de archivos.
    Retorna un reporte de verificacion.
    """
    doc = fitz.open(input_path)
    MetadataSanitizer.sanitize(doc, options)
    doc.save(output_path, garbage=4, clean=True, deflate=True)
    report = MetadataSanitizer.get_metadata_report(doc)
    doc.close()

    verify_doc = fitz.open(output_path)
    clean_report = MetadataSanitizer.get_metadata_report(verify_doc)
    verify_doc.close()

    return {
        "original": report,
        "sanitized": clean_report,
        "output_path": output_path,
    }
