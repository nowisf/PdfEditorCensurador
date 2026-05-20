import os
import uuid
import fitz
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from typing import List
import json

from ..models.schemas import RedactionZone, ImageRedactionMethod
from ..services.pdf_redaction import RedactionEngine
from ..config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, safe_remove

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/redaction", tags=["Redaccion"])


def _read_and_validate(file: UploadFile):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")
    content = b""
    chunks = []
    total = 0
    while True:
        chunk = asyncio_run_sync_or_read(file)
        if not chunk:
            break
    return content


async def _save_upload(file: UploadFile) -> tuple[str, bytes]:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"Archivo excede {MAX_FILE_SIZE // (1024*1024)}MB")
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(content)
    return tmp_path, content


def _close_doc(doc):
    if doc:
        try:
            doc.close()
        except Exception:
            pass


@router.post("/render-page")
async def render_page(
    file: UploadFile = File(...),
    page: int = Form(0),
    dpi: int = Form(150),
):
    tmp_path, _ = await _save_upload(file)
    doc = None
    try:
        doc = fitz.open(tmp_path)
        if doc.is_encrypted:
            raise HTTPException(400, "El PDF esta encriptado. Desproteja primero.")
        if page >= len(doc):
            raise HTTPException(400, f"Pagina {page} fuera de rango (total: {len(doc)})")

        page_obj = doc[page]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page_obj.get_pixmap(matrix=mat)

        img_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}_page_{page}.png")
        pix.save(img_path)
        doc.close()
        doc = None

        return FileResponse(img_path, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error renderizando pagina: {str(e)}")
    finally:
        _close_doc(doc)
        safe_remove(tmp_path)


@router.post("/page-info")
async def get_page_info(file: UploadFile = File(...)):
    tmp_path, _ = await _save_upload(file)
    doc = None
    try:
        doc = fitz.open(tmp_path)
        if doc.is_encrypted:
            raise HTTPException(400, "El PDF esta encriptado. Desproteja primero.")
        pages = []
        for i in range(len(doc)):
            page = doc[i]
            pages.append({
                "index": i,
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
            })
        doc.close()
        doc = None
        return {"pages": pages, "total": len(pages)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error leyendo PDF: {str(e)}")
    finally:
        _close_doc(doc)
        safe_remove(tmp_path)


@router.post("/apply-redaction")
async def apply_redaction(
    file: UploadFile = File(...),
    zones_json: str = Form(...),
    image_method: str = Form("blackout"),
    pixelate_block_size: int = Form(15),
):
    tmp_path, _ = await _save_upload(file)

    try:
        zones_data = json.loads(zones_json)
        zones = [RedactionZone(**z) for z in zones_data]
    except Exception as e:
        raise HTTPException(400, f"Zonas de redaccion invalidas: {str(e)}")

    doc = None
    output_path = None
    try:
        doc = fitz.open(tmp_path)
        method = ImageRedactionMethod(image_method)

        RedactionEngine.apply_all_redactions(
            doc, zones,
            image_method=method,
            pixelate_block_size=pixelate_block_size,
        )

        output_filename = f"REDACTED_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, clean=True, deflate=True)
        doc.close()
        doc = None

        verify_doc = fitz.open(output_path)
        verification = _verify_all_redactions(verify_doc, zones)
        verify_doc.close()

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
            headers={"X-Redaction-Verified": str(verification["all_clean"])},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en redaccion: {e}")
        raise HTTPException(500, f"Error aplicando redaccion: {str(e)}")
    finally:
        _close_doc(doc)
        safe_remove(tmp_path)


@router.post("/extract-text")
async def extract_text(file: UploadFile = File(...), page: int = Form(0)):
    tmp_path, _ = await _save_upload(file)
    doc = None
    try:
        doc = fitz.open(tmp_path)
        if page >= len(doc):
            raise HTTPException(400, "Pagina fuera de rango")
        page_obj = doc[page]
        text = page_obj.get_text("text")
        doc.close()
        doc = None
        return {"page": page, "text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error extrayendo texto: {str(e)}")
    finally:
        _close_doc(doc)
        safe_remove(tmp_path)


def _verify_all_redactions(doc: fitz.Document, zones: List[RedactionZone]) -> dict:
    results = []
    for zone in zones:
        rect = fitz.Rect(zone.x, zone.y, zone.x + zone.width, zone.y + zone.height)
        is_clean = RedactionEngine.verify_redaction(doc, zone.page, rect)
        results.append({
            "page": zone.page,
            "zone": {"x": zone.x, "y": zone.y, "w": zone.width, "h": zone.height},
            "clean": is_clean,
        })
    return {
        "zones": results,
        "all_clean": all(r["clean"] for r in results),
    }
