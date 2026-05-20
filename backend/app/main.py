import os
import uuid
import fitz
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, UPLOAD_DIR, OUTPUT_DIR, MAX_FILE_SIZE, safe_remove, ERROR_CODES
from .routes import redaction, metadata, signature, converter, tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Censura - Motor de Redaccion Irreversible",
    description="Sistema de gestion y censura segura de PDFs para Transparencia Activa",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(redaction.router)
app.include_router(metadata.router)
app.include_router(signature.router)
app.include_router(converter.router)
app.include_router(tools.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"Archivo excede el limite de {MAX_FILE_SIZE // (1024*1024)}MB")

    file_id = uuid.uuid4().hex
    tmp_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(content)

    doc = None
    try:
        doc = fitz.open(tmp_path)
        info = {
            "file_id": file_id,
            "filename": file.filename,
            "size_bytes": len(content),
            "pages": len(doc),
            "page_details": [],
        }
        for i in range(len(doc)):
            page = doc[i]
            info["page_details"].append({
                "index": i,
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
            })
        metadata = doc.metadata
        info["metadata"] = {k: v for k, v in metadata.items() if v}
        doc.close()
        doc = None
        return info
    except Exception as e:
        logger.error(f"Error procesando PDF: {e}")
        raise HTTPException(500, ERROR_CODES["ERR_PDF_PARSE"])
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass
        safe_remove(tmp_path)
