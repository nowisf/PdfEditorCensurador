import os
import tempfile
import atexit
import shutil
import logging
from starlette.responses import FileResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_censura_uploads")
OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "pdf_censura_output")
MAX_FILE_SIZE = 100 * 1024 * 1024

PDF_MAGIC_BYTES = [b'%PDF-1', b'%PDF-2']

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def validate_pdf_upload(content: bytes, filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Solo se aceptan archivos PDF")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"Archivo excede el limite de {MAX_FILE_SIZE // (1024*1024)}MB")
    if not any(content[:8].startswith(magic) for magic in PDF_MAGIC_BYTES):
        raise ValueError("El archivo no es un PDF valido (magic bytes incorrectos)")


def safe_remove(*paths):
    for p in paths:
        if not p:
            continue
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            logger.warning(f"No se pudo eliminar archivo temporal: {p}")


class TempFileResponse(FileResponse):
    def __init__(self, path, cleanup_after=None, **kwargs):
        self._cleanup_after = cleanup_after or []
        super().__init__(path, **kwargs)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            for p in self._cleanup_after:
                safe_remove(p)


def cleanup_temp_dirs():
    for d in [UPLOAD_DIR, OUTPUT_DIR]:
        try:
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


atexit.register(cleanup_temp_dirs)


def get_cors_origins():
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    vercel_url = os.environ.get("VERCEL_URL", "")
    if vercel_url:
        origins.append(f"https://{vercel_url}")
    return origins


CORS_ORIGINS = get_cors_origins()


ERROR_CODES = {
    "ERR_PDF_INVALID": "El archivo proporcionado no es un PDF valido",
    "ERR_PDF_TOO_LARGE": "El archivo excede el tamano maximo permitido",
    "ERR_PDF_ENCRYPTED": "El PDF esta encriptado y no puede procesarse",
    "ERR_PDF_PARSE": "Error al procesar el archivo PDF",
    "ERR_REDACTION_VERIFY": "La verificacion de censura fallo - el archivo no fue modificado",
    "ERR_SIGNATURE": "Error en el proceso de firma digital",
    "ERR_METADATA": "Error en el proceso de saneamiento de metadatos",
    "ERR_INTERNAL": "Error interno del servidor",
}
