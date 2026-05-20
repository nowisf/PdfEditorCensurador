import os
import uuid
import fitz
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import json

from ..models.schemas import MetadataSanitizeOptions
from ..services.pdf_metadata import MetadataSanitizer
from ..config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, safe_remove, TempFileResponse, ERROR_CODES, validate_pdf_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["Metadatos"])


def _close_doc(doc):
    if doc:
        try:
            doc.close()
        except Exception:
            pass


@router.post("/inspect")
async def inspect_metadata(file: UploadFile = File(...)):
    content = await file.read()`n    try:`n        validate_pdf_upload(content, file.filename)`n    except ValueError as e:`n        raise HTTPException(400, str(e))

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(content)

    doc = None
    try:
        doc = fitz.open(tmp_path)
        report = MetadataSanitizer.get_metadata_report(doc)
        doc.close()
        doc = None
        return report
    except Exception as e:
        logger.error(f"Error inspeccionando metadatos: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_METADATA"])
    finally:
        _close_doc(doc)
        safe_remove(tmp_path)


@router.post("/sanitize")
async def sanitize_metadata(
    file: UploadFile = File(...),
    options_json: str = Form("{}"),
):
    content = await file.read()`n    try:`n        validate_pdf_upload(content, file.filename)`n    except ValueError as e:`n        raise HTTPException(400, str(e))

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        options_data = json.loads(options_json)
        options = MetadataSanitizeOptions(**options_data)
    except Exception:
        options = MetadataSanitizeOptions()

    doc = None
    try:
        doc = fitz.open(tmp_path)
        before_report = MetadataSanitizer.get_metadata_report(doc)
        MetadataSanitizer.sanitize(doc, options)

        output_filename = f"SANITIZED_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, clean=True, deflate=True)
        doc.close()
        doc = None

        verify_doc = fitz.open(output_path)
        after_report = MetadataSanitizer.get_metadata_report(verify_doc)
        verify_doc.close()

        return TempFileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
            cleanup_after=[output_path],
            headers={
                "X-Metadata-Before": str(before_report),
                "X-Metadata-After": str(after_report),
            },
        )
    except Exception as e:
        logger.error(f"Error en saneamiento: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_METADATA"])
    finally:
        _close_doc(doc)
        safe_remove(tmp_path)
