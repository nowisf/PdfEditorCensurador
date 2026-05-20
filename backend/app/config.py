import os
import tempfile
import atexit
import shutil
import logging

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_censura_uploads")
OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "pdf_censura_output")
MAX_FILE_SIZE = 100 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def safe_remove(*paths):
    for p in paths:
        if not p:
            continue
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            logger.warning(f"No se pudo eliminar archivo temporal: {p}")


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
