import os
import uuid
import fitz
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import json

from ..models.schemas import MetadataSanitizeOptions
from ..services.pdf_metadata import MetadataSanitizer
from ..config import UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["Metadatos"])


@router.post("/inspect")
async def inspect_metadata(file: UploadFile = File(...)):
    """Inspecciona todos los metadatos del PDF antes del saneamiento."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        doc = fitz.open(tmp_path)
        report = MetadataSanitizer.get_metadata_report(doc)
        doc.close()
        return report
    except Exception as e:
        raise HTTPException(500, f"Error inspeccionando metadatos: {str(e)}")


@router.post("/sanitize")
async def sanitize_metadata(
    file: UploadFile = File(...),
    options_json: str = Form("{}"),
):
    """
    Ejecuta saneamiento destructivo de todos los metadatos del PDF.
    
    La operacion es IRREVERSIBLE. Se sobreescriben todos los campos,
    se destruyen flujos XMP, miniaturas y datos ocultos.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        options_data = json.loads(options_json)
        options = MetadataSanitizeOptions(**options_data)
    except Exception:
        options = MetadataSanitizeOptions()

    try:
        doc = fitz.open(tmp_path)
        before_report = MetadataSanitizer.get_metadata_report(doc)
        MetadataSanitizer.sanitize(doc, options)

        output_filename = f"SANITIZED_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, clean=True, deflate=True)
        doc.close()

        verify_doc = fitz.open(output_path)
        after_report = MetadataSanitizer.get_metadata_report(verify_doc)
        verify_doc.close()

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
            headers={
                "X-Metadata-Before": str(before_report),
                "X-Metadata-After": str(after_report),
            },
        )
    except Exception as e:
        logger.error(f"Error en saneamiento: {e}")
        raise HTTPException(500, f"Error saneando metadatos: {str(e)}")
