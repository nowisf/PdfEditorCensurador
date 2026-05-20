"""
Pruebas unitarias para signature, converter, protection, pages, watermark, sensitive.
"""

import os
import sys
import tempfile
import fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import create_test_pdf, create_test_pdf_with_metadata
from app.services.pdf_signature import PDFSignature, PDFProtection
from app.services.pdf_converter import PDFConverter
from app.services.pdf_pages import PageManager
from app.services.pdf_watermark import Watermarker
from app.services.pdf_sensitive import SensitiveDataDetector
from app.models.schemas import ProtectionOptions, SignaturePosition


class TestSignature:
    def test_visual_signature_creates_valid_pdf(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            pos = SignaturePosition(page=0, x=72, y=400, width=300, height=100)
            PDFSignature.add_visual_signature(doc, pos, signer_name="TestUser", signer_rut="12345678-9")
            output = tempfile.mktemp(suffix=".pdf")
            doc.save(output)
            doc.close()

            verify = fitz.open(output)
            assert len(verify) == 1
            assert verify[0].rect.width == 612
            verify.close()
            os.unlink(output)
        finally:
            os.unlink(pdf_path)

    def test_document_hash_computed(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            h = PDFSignature._compute_document_hash(doc)
            assert len(h) == 64
            assert h.isalnum()
            doc.close()
        finally:
            os.unlink(pdf_path)


class TestProtection:
    def test_save_protected_creates_file(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            output = tempfile.mktemp(suffix=".pdf")
            opts = ProtectionOptions(owner_password="admin", user_password="user", encryption_level=256)
            PDFProtection.save_protected(doc, output, opts)
            doc.close()

            assert os.path.exists(output)
            assert os.path.getsize(output) > 0
            os.unlink(output)
        finally:
            os.unlink(pdf_path)

    def test_protected_pdf_requires_password(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            output = tempfile.mktemp(suffix=".pdf")
            opts = ProtectionOptions(owner_password="secret123", allow_print=False, allow_copy=False)
            PDFProtection.save_protected(doc, output, opts)
            doc.close()

            raw = open(output, "rb").read()
            assert b"/Encrypt" in raw
            os.unlink(output)
        finally:
            os.unlink(pdf_path)


class TestConverter:
    def test_create_pdf_from_text(self):
        output = tempfile.mktemp(suffix=".pdf")
        PDFConverter.create_pdf_from_text("Hello world test", output)
        assert os.path.exists(output)
        doc = fitz.open(output)
        assert len(doc) == 1
        assert "Hello world test" in doc[0].get_text()
        doc.close()
        os.unlink(output)

    def test_merge_pdfs(self):
        paths = []
        for i in range(3):
            p = tempfile.mktemp(suffix=".pdf")
            PDFConverter.create_pdf_from_text(f"Page {i}", p)
            paths.append(p)

        output = tempfile.mktemp(suffix=".pdf")
        PDFConverter.merge_pdfs(paths, output)

        doc = fitz.open(output)
        assert len(doc) == 3
        doc.close()
        os.unlink(output)
        for p in paths:
            os.unlink(p)


class TestPageManager:
    def test_rotate_pages(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            PageManager.rotate_pages(doc, [0], 90)
            assert doc[0].rotation == 90
            doc.close()
        finally:
            os.unlink(pdf_path)

    def test_delete_pages(self):
        paths = []
        for i in range(3):
            p = tempfile.mktemp(suffix=".pdf")
            PDFConverter.create_pdf_from_text(f"Page {i}", p)
            paths.append(p)

        merged = tempfile.mktemp(suffix=".pdf")
        PDFConverter.merge_pdfs(paths, merged)
        for p in paths:
            os.unlink(p)

        doc = fitz.open(merged)
        assert len(doc) == 3
        PageManager.delete_pages(doc, [1])
        assert len(doc) == 2
        doc.close()
        os.unlink(merged)


class TestWatermark:
    def test_watermark_applied(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            Watermarker.apply_text_watermark(doc, text="TEST WM")
            output = tempfile.mktemp(suffix=".pdf")
            doc.save(output)
            doc.close()

            verify = fitz.open(output)
            text = verify[0].get_text("text")
            assert "TEST WM" in text
            verify.close()
            os.unlink(output)
        finally:
            os.unlink(pdf_path)

    def test_stamp_applied(self):
        pdf_path = create_test_pdf()
        try:
            doc = fitz.open(pdf_path)
            Watermarker.apply_stamp(doc, text="SELLADO")
            output = tempfile.mktemp(suffix=".pdf")
            doc.save(output)
            doc.close()

            verify = fitz.open(output)
            text = verify[0].get_text("text")
            assert "SELLADO" in text
            verify.close()
            os.unlink(output)
        finally:
            os.unlink(pdf_path)


class TestSensitiveDetector:
    def test_detect_rut(self):
        output = tempfile.mktemp(suffix=".pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(fitz.Point(72, 72), "El RUT del funcionario es 12.345.678-9", fontsize=12)
        doc.save(output)
        doc.close()

        doc = fitz.open(output)
        report = SensitiveDataDetector.get_detection_report(doc)
        assert report["total"] >= 1
        found = any(d["type"] == "rut" for d in report["detections"])
        assert found, "RUT no detectado"
        doc.close()
        os.unlink(output)

    def test_detect_email(self):
        output = tempfile.mktemp(suffix=".pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(fitz.Point(72, 72), "Contacto: juan.perez@gob.cl", fontsize=12)
        doc.save(output)
        doc.close()

        doc = fitz.open(output)
        report = SensitiveDataDetector.get_detection_report(doc)
        assert report["total"] >= 1
        found = any(d["type"] == "email" for d in report["detections"])
        assert found, "Email no detectado"
        doc.close()
        os.unlink(output)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
