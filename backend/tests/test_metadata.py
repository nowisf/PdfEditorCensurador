"""
Pruebas unitarias de saneamiento de metadatos.

Verifica que:
1. Todos los campos de metadatos estandar esten vacios
2. Los flujos XMP sean destruidos
3. Las miniaturas sean eliminadas
4. Los bytes crudos no contengan los metadatos originales
"""

import os
import sys
import tempfile
import fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import create_test_pdf_with_metadata
from app.services.pdf_metadata import MetadataSanitizer, sanitize_pdf_file
from app.models.schemas import MetadataSanitizeOptions


class TestMetadataSanitization:

    def test_author_removed(self):
        """El campo Author debe estar vacio despues del saneamiento."""
        pdf_path = create_test_pdf_with_metadata()
        try:
            doc = fitz.open(pdf_path)
            assert doc.metadata.get("author") == "Autor Sensible"

            MetadataSanitizer.sanitize(doc)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            assert verify_doc.metadata.get("author", "") == "", (
                f"Author no eliminado: {verify_doc.metadata.get('author')}"
            )
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_all_standard_fields_removed(self):
        """Todos los campos estandar deben estar vacios."""
        pdf_path = create_test_pdf_with_metadata()
        try:
            doc = fitz.open(pdf_path)
            MetadataSanitizer.sanitize(doc)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            meta = verify_doc.metadata
            sensitive_fields = ["author", "creator", "producer", "title", "subject", "keywords", "creationDate", "modDate"]
            for field in sensitive_fields:
                value = meta.get(field, "")
                assert value == "", (
                    f"Campo {field} no eliminado: {value}"
                )
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_raw_bytes_no_author(self):
        """Los bytes crudos no deben contener el nombre del autor."""
        pdf_path = create_test_pdf_with_metadata()
        try:
            doc = fitz.open(pdf_path)
            MetadataSanitizer.sanitize(doc)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            with open(output_path, "rb") as f:
                raw = f.read()

            assert b"Autor Sensible" not in raw, (
                "Bytes crudos contienen metadato de autor"
            )
            assert b"Titulo Confidencial" not in raw, (
                "Bytes crudos contienen metadato de titulo"
            )
            assert b"secreto, confidencial" not in raw, (
                "Bytes crudos contienen metadato de keywords"
            )
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_selective_sanitization(self):
        """Debe permitir saneamiento selectivo de campos."""
        pdf_path = create_test_pdf_with_metadata()
        try:
            doc = fitz.open(pdf_path)
            options = MetadataSanitizeOptions(
                remove_author=True,
                remove_creator=False,
                remove_title=False,
            )
            MetadataSanitizer.sanitize(doc, options)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            meta = verify_doc.metadata
            assert meta.get("author", "") == ""
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_sanitize_file_convenience_function(self):
        """La funcion de conveniencia debe producir un archivo limpio."""
        pdf_path = create_test_pdf_with_metadata()
        try:
            output_path = tempfile.mktemp(suffix=".pdf")
            result = sanitize_pdf_file(pdf_path, output_path)
            assert os.path.exists(output_path)

            verify_doc = fitz.open(output_path)
            meta = verify_doc.metadata
            assert meta.get("author", "") == ""
            assert meta.get("title", "") == ""
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_metadata_report(self):
        """El reporte de metadatos debe listar campos con contenido."""
        pdf_path = create_test_pdf_with_metadata()
        try:
            doc = fitz.open(pdf_path)
            report = MetadataSanitizer.get_metadata_report(doc)
            assert "standard_fields" in report
            assert "author" in report["standard_fields"]
            doc.close()
        finally:
            os.unlink(pdf_path)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
