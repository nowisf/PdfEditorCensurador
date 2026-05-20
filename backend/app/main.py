import os
import uuid
import fitz
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, UPLOAD_DIR, OUTPUT_DIR
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
    """Sube un PDF y retorna informacion basica."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    file_id = uuid.uuid4().hex
    tmp_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

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
        return info
    except Exception as e:
        raise HTTPException(500, f"Error procesando PDF: {str(e)}")


@app.get("/api/file/{file_id}")
async def get_file(file_id: str):
    """Recupera un archivo subido por su ID."""
    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(file_id):
            path = os.path.join(UPLOAD_DIR, fname)
            return FileResponse(path, media_type="application/pdf")
    raise HTTPException(404, "Archivo no encontrado")
