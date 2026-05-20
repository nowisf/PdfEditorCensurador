import os
import uuid
import zipfile
import logging
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse

from ..services.pdf_converter import PDFConverter
from ..config import UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, safe_remove, TempFileResponse, ERROR_CODES, validate_pdf_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/converter", tags=["Conversion"])


@router.post("/images-to-pdf")
async def images_to_pdf(files: List[UploadFile] = File(...)):
    image_paths = []
    try:
        for f in files:
            content = await f.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(413, f"Archivo {f.filename} excede el limite")
            tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{f.filename}")
            with open(tmp_path, "wb") as out:
                out.write(content)
            image_paths.append(tmp_path)

        output_filename = f"converted_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        PDFConverter.images_to_pdf(image_paths, output_path)

        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error convirtiendo imagenes a PDF: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])
    finally:
        for p in image_paths:
            safe_remove(p)


@router.post("/pdf-to-images")
async def pdf_to_images(file: UploadFile = File(...), dpi: int = Form(200)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Archivo excede el limite")
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        output_dir = os.path.join(OUTPUT_DIR, f"images_{uuid.uuid4().hex}")
        os.makedirs(output_dir, exist_ok=True)
        paths = PDFConverter.pdf_to_images(tmp_path, output_dir, dpi=dpi)

        zip_path = os.path.join(OUTPUT_DIR, f"pages_{uuid.uuid4().hex}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                zf.write(p, os.path.basename(p))

        return TempFileResponse(zip_path, media_type="application/zip", filename="paginas.zip", cleanup_after=[zip_path])
    except Exception as e:
        logger.error(f"Error convirtiendo PDF a imagenes: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])
    finally:
        safe_remove(tmp_path)


@router.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    pdf_paths = []
    try:
        for f in files:
            content = await f.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(413, f"Archivo {f.filename} excede el limite")
            tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{f.filename}")
            with open(tmp_path, "wb") as out:
                out.write(content)
            pdf_paths.append(tmp_path)

        output_filename = f"merged_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        PDFConverter.merge_pdfs(pdf_paths, output_path)

        return TempFileResponse(output_path, media_type="application/pdf", filename=output_filename, cleanup_after=[output_path])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error combinando PDFs: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_INTERNAL"])
    finally:
        for p in pdf_paths:
            safe_remove(p)
