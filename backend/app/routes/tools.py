import os
import uuid
import json
import fitz
import logging
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse

from ..services.pdf_sensitive import SensitiveDataDetector
from ..services.pdf_pages import PageManager
from ..services.pdf_watermark import Watermarker
from ..services.audit_log import AuditLogger
from ..config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, safe_remove, ERROR_CODES, validate_pdf_upload, TempFileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["Herramientas"])


@router.post("/detect-sensitive")
async def detect_sensitive(file: UploadFile = File(...)):
    """Detecta automaticamente datos sensibles (RUT, emails, telefonos, etc)."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        doc = fitz.open(tmp_path)
        report = SensitiveDataDetector.get_detection_report(doc)
        doc.close()

        AuditLogger.log_operation("detect_sensitive", file.filename, {"found": report["total"]})
        return report
    except Exception as e:
        logger.error(f"Error detectando datos: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.post("/rotate-pages")
async def rotate_pages(
    file: UploadFile = File(...),
    pages_json: str = Form("[]"),
    degrees: int = Form(90),
):
    """Rota paginas del PDF."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        page_indices = json.loads(pages_json)
        doc = fitz.open(tmp_path)
        if not page_indices:
            page_indices = list(range(len(doc)))
        PageManager.rotate_pages(doc, page_indices, degrees)

        output_filename = f"rotated_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        AuditLogger.log_operation("rotate_pages", file.filename, {"pages": page_indices, "degrees": degrees})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except Exception as e:
        logger.error(f"Error rotando paginas: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.post("/delete-pages")
async def delete_pages(
    file: UploadFile = File(...),
    pages_json: str = Form(...),
):
    """Elimina paginas del PDF."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        page_indices = json.loads(pages_json)
        doc = fitz.open(tmp_path)
        PageManager.delete_pages(doc, page_indices)

        output_filename = f"pages_removed_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        AuditLogger.log_operation("delete_pages", file.filename, {"pages_removed": page_indices})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except Exception as e:
        logger.error(f"Error eliminando paginas: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.post("/reorder-pages")
async def reorder_pages(
    file: UploadFile = File(...),
    order_json: str = Form(...),
):
    """Reordena paginas del PDF."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        new_order = json.loads(order_json)
        doc = fitz.open(tmp_path)
        new_doc = PageManager.reorder_pages(doc, new_order)

        output_filename = f"reordered_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        new_doc.save(output_path, garbage=4, deflate=True)
        new_doc.close()
        doc.close()

        AuditLogger.log_operation("reorder_pages", file.filename, {"new_order": new_order})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except Exception as e:
        logger.error(f"Error reordenando paginas: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.post("/watermark")
async def apply_watermark(
    file: UploadFile = File(...),
    text: str = Form("CONFIDENCIAL"),
    opacity: float = Form(0.15),
    angle: int = Form(45),
    fontsize: float = Form(60),
):
    """Aplica marca de agua al PDF."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        doc = fitz.open(tmp_path)
        Watermarker.apply_text_watermark(doc, text=text, opacity=opacity, angle=angle, fontsize=fontsize)

        output_filename = f"watermarked_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        AuditLogger.log_operation("watermark", file.filename, {"text": text})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except Exception as e:
        logger.error(f"Error aplicando marca de agua: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.post("/stamp")
async def apply_stamp(
    file: UploadFile = File(...),
    text: str = Form("CENSURADO"),
    page: int = Form(0),
    x: float = Form(400),
    y: float = Form(50),
):
    """Aplica sello de texto en posicion especifica."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        doc = fitz.open(tmp_path)
        Watermarker.apply_stamp(doc, text=text, page_idx=page, x=x, y=y)

        output_filename = f"stamped_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        AuditLogger.log_operation("stamp", file.filename, {"text": text, "page": page})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except Exception as e:
        logger.error(f"Error aplicando sello: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.get("/audit-logs")
async def get_audit_logs(date: str = None, limit: int = 100):
    """Obtiene logs de auditoria."""
    logs = AuditLogger.get_logs(date=date, limit=limit)
    return {"logs": logs, "count": len(logs)}


@router.get("/audit-stats")
async def get_audit_stats():
    """Obtiene estadisticas de auditoria."""
    return AuditLogger.get_stats()


@router.post("/batch-redact")
async def batch_redact(
    files: List[UploadFile] = File(...),
    zones_json: str = Form(...),
    image_method: str = Form("blackout"),
):
    """Aplica las mismas zonas de censura a multiples PDFs."""
    from ..models.schemas import RedactionZone, RedactionType
    from ..services.pdf_redaction import RedactionEngine

    try:
        zones_data = json.loads(zones_json)
        zones = [RedactionZone(**z) for z in zones_data]
    except Exception as e:
        raise HTTPException(400, f"Zonas invalidas: {str(e)}")

    results = []
    for upload_file in files:
        tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{upload_file.filename}")
        content = await upload_file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        try:
            doc = fitz.open(tmp_path)
            RedactionEngine.apply_all_redactions(doc, zones)
            output_filename = f"BATCH_REDACTED_{uuid.uuid4().hex}_{upload_file.filename}"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            doc.save(output_path, garbage=4, clean=True, deflate=True)
            doc.close()
            results.append({"filename": output_filename, "status": "ok"})
            AuditLogger.log_operation("batch_redact", upload_file.filename, {"zones": len(zones)})
        except Exception as e:
            results.append({"filename": upload_file.filename, "status": "error", "error": str(e)})

    return {"results": results, "processed": len(results)}


@router.post("/add-pages")
async def add_pages(
    file: UploadFile = File(...),
    count: int = Form(1),
    position: str = Form("end"),
    width: float = Form(612),
    height: float = Form(792),
    content: str = Form(""),
):
    """
    Agrega paginas al PDF.
    - count: numero de paginas a agregar
    - position: 'start', 'end', o indice numerico como string
    - width/height: dimensiones en puntos (612x792 = Letter, 595x842 = A4)
    - content: texto opcional para llenar las nuevas paginas
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    file_content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(file_content)

    try:
        doc = fitz.open(tmp_path)

        for _ in range(count):
            new_page = doc.new_page(width=width, height=height)
            if content:
                text_rect = fitz.Rect(36, 36, width - 36, height - 36)
                new_page.insert_textbox(
                    text_rect,
                    content,
                    fontsize=11,
                    fontname="helv",
                    color=(0, 0, 0),
                )

        if position == "start":
            doc.move_page(len(doc) - 1, 0)
        elif position.isdigit():
            idx = min(int(position), len(doc) - 1)
            doc.move_page(len(doc) - 1, idx)

        output_filename = f"pages_added_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        AuditLogger.log_operation("add_pages", file.filename, {"count": count, "position": position})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except Exception as e:
        logger.error(f"Error agregando paginas: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])


@router.post("/add-text")
async def add_text(
    file: UploadFile = File(...),
    page: int = Form(0),
    x: float = Form(72),
    y: float = Form(72),
    width: float = Form(200),
    height: float = Form(50),
    text: str = Form(...),
    fontsize: float = Form(12),
    fontname: str = Form("helv"),
    color_r: float = Form(0),
    color_g: float = Form(0),
    color_b: float = Form(0),
    align: int = Form(0),
    fontfile: UploadFile = File(None),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    file_content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(file_content)

    font_tmp = None
    if fontfile and fontfile.filename:
        ext = os.path.splitext(fontfile.filename)[1].lower()
        if ext not in (".ttf", ".otf"):
            raise HTTPException(400, "Solo se aceptan fuentes TTF u OTF")
        font_content = await fontfile.read()
        font_tmp = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{fontfile.filename}")
        with open(font_tmp, "wb") as f:
            f.write(font_content)

    doc = None
    try:
        doc = fitz.open(tmp_path)
        if doc.is_encrypted:
            raise HTTPException(400, "El PDF esta encriptado. Desproteja primero.")
        if page >= len(doc):
            raise HTTPException(400, f"Pagina {page} fuera de rango (total: {len(doc)})")

        target_page = doc[page]
        rect = fitz.Rect(x, y, x + width, y + height)

        kwargs = dict(
            rect=rect,
            buffer=text,
            fontsize=fontsize,
            color=(color_r, color_g, color_b),
            align=align,
        )
        if font_tmp:
            kwargs["fontname"] = "customfont"
            kwargs["fontfile"] = font_tmp
        else:
            kwargs["fontname"] = fontname

        target_page.insert_textbox(**kwargs)

        output_filename = f"text_added_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        doc = None

        AuditLogger.log_operation("add_text", file.filename, {"page": page, "text_length": len(text), "font": fontname})
        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error agregando texto: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass
        for p in [font_tmp, tmp_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
