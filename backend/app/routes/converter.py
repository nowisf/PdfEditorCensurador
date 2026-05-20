import os
import uuid
import zipfile
import logging
import tempfile
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, StreamingResponse

from ..services.pdf_converter import PDFConverter
from ..config import UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/converter", tags=["Conversion"])


@router.post("/images-to-pdf")
async def images_to_pdf(
    files: List[UploadFile] = File(...),
):
    """Convierte imagenes a un PDF."""
    image_paths = []
    for f in files:
        tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{f.filename}")
        content = await f.read()
        with open(tmp_path, "wb") as out:
            out.write(content)
        image_paths.append(tmp_path)

    try:
        output_filename = f"converted_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        PDFConverter.images_to_pdf(image_paths, output_path)

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
        )
    except Exception as e:
        raise HTTPException(500, f"Error convirtiendo: {str(e)}")


@router.post("/pdf-to-images")
async def pdf_to_images(
    file: UploadFile = File(...),
    dpi: int = Form(200),
):
    """Convierte un PDF a imagenes (una por pagina)."""
    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
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

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="paginas.zip",
        )
    except Exception as e:
        raise HTTPException(500, f"Error convirtiendo: {str(e)}")


@router.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    """Combina multiples PDFs en uno solo."""
    pdf_paths = []
    for f in files:
        tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{f.filename}")
        content = await f.read()
        with open(tmp_path, "wb") as out:
            out.write(content)
        pdf_paths.append(tmp_path)

    try:
        output_filename = f"merged_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        PDFConverter.merge_pdfs(pdf_paths, output_path)

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
        )
    except Exception as e:
        raise HTTPException(500, f"Error combinando PDFs: {str(e)}")
