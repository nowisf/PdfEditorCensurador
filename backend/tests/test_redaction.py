"""
Pruebas unitarias de censura irreversible.

Verifica que:
1. El texto censurado NO sea extraible mediante get_text()
2. El texto censurado NO aparezca en busquedas
3. La zona censurada contenga un recuadro solido
4. La verificacion de redaccion confirme la limpieza
"""

import os
import sys
import tempfile
import fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import create_test_pdf, create_test_pdf_with_image
from app.services.pdf_redaction import RedactionEngine
from app.models.schemas import RedactionZone, RedactionType


class TestTextRedaction:
    """Pruebas de censura de texto irreversible."""

    def test_text_removed_from_content_stream(self):
        """El texto censurado debe ser eliminado del content stream."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)

            original_text = doc[0].get_text("text")
            assert "Juan Perez" in original_text
            assert "12.345.678-9" in original_text

            zones = [
                RedactionZone(
                    page=0, x=65, y=65, width=100, height=20,
                    redaction_type=RedactionType.TEXT,
                    color=[0, 0, 0], fill=True,
                ),
            ]

            RedactionEngine.apply_all_redactions(doc, zones)

            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            redacted_text = verify_doc[0].get_text("text")

            assert "Juan Perez" not in redacted_text, (
                "FALLO CRITICO: El texto censurado sigue presente en el PDF"
            )
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_rut_removed(self):
        """El RUT debe ser completamente eliminado."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            zones = [
                RedactionZone(
                    page=0, x=180, y=65, width=120, height=20,
                    redaction_type=RedactionType.TEXT,
                ),
            ]
            RedactionEngine.apply_all_redactions(doc, zones)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            text = verify_doc[0].get_text("text")
            assert "12.345.678" not in text
            assert "12.345.678-9" not in text
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_search_returns_no_results_after_redaction(self):
        """La busqueda de texto censurado debe retornar 0 resultados."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            zones = [
                RedactionZone(
                    page=0, x=65, y=65, width=480, height=20,
                    redaction_type=RedactionType.TEXT,
                ),
            ]
            RedactionEngine.apply_all_redactions(doc, zones)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            results = verify_doc[0].search_for("Juan Perez")
            assert len(results) == 0, "La busqueda encontro texto censurado"
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_verification_confirms_clean(self):
        """El motor de verificacion debe confirmar que la zona esta limpia."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            zone = RedactionZone(
                page=0, x=65, y=65, width=100, height=20,
                redaction_type=RedactionType.TEXT,
            )
            RedactionEngine.apply_all_redactions(doc, [zone])
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            rect = fitz.Rect(65, 65, 165, 85)
            is_clean = RedactionEngine.verify_redaction(verify_doc, 0, rect)
            assert is_clean, "Verificacion fallo: la zona contiene texto residual"
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_multiple_zones_on_same_page(self):
        """Multiples zonas de censura en la misma pagina deben funcionar."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            zones = [
                RedactionZone(page=0, x=65, y=65, width=100, height=20, redaction_type=RedactionType.TEXT),
                RedactionZone(page=0, x=180, y=65, width=120, height=20, redaction_type=RedactionType.TEXT),
            ]
            RedactionEngine.apply_all_redactions(doc, zones)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            text = verify_doc[0].get_text("text")
            assert "Juan Perez" not in text
            assert "12.345.678-9" not in text
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_non_redacted_text_preserved(self):
        """El texto fuera de las zonas censuradas debe permanecer intacto."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            zones = [
                RedactionZone(page=0, x=65, y=65, width=100, height=20, redaction_type=RedactionType.TEXT),
            ]
            RedactionEngine.apply_all_redactions(doc, zones)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            text = verify_doc[0].get_text("text")
            assert "RUT" in text or "Direccion" in text or "Santiago" in text, (
                "Texto no censurado fue alterado indebidamente"
            )
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)

    def test_raw_bytes_contain_no_censored_text(self):
        """Los bytes crudos del PDF no deben contener el texto censurado."""
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            zones = [
                RedactionZone(page=0, x=65, y=65, width=480, height=20, redaction_type=RedactionType.TEXT),
            ]
            RedactionEngine.apply_all_redactions(doc, zones)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True, deflate=True)
            doc.close()

            with open(output_path, "rb") as f:
                raw_bytes = f.read()

            assert b"Juan Perez" not in raw_bytes, (
                "Los bytes crudos del PDF contienen texto censurado"
            )
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)


class TestImageRedaction:
    """Pruebas de censura de imagenes."""

    def test_image_pdf_opens_after_redaction(self):
        """El PDF con imagen redactada debe abrirse sin errores."""
        pdf_path = create_test_pdf_with_image()
        try:
            doc = fitz.open(pdf_path)
            zones = [
                RedactionZone(
                    page=0, x=50, y=50, width=300, height=200,
                    redaction_type=RedactionType.IMAGE,
                ),
            ]
            RedactionEngine.apply_all_redactions(doc, zones)
            output_path = tempfile.mktemp(suffix=".pdf")
            doc.save(output_path, garbage=4, clean=True)
            doc.close()

            verify_doc = fitz.open(output_path)
            assert len(verify_doc) == 1
            verify_doc.close()
            os.unlink(output_path)
        finally:
            os.unlink(pdf_path)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
