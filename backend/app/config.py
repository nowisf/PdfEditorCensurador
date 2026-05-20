import os
import tempfile

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "pdf_censura_uploads")
OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "pdf_censura_output")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    os.environ.get("VERCEL_URL", ""),
    "https://" + os.environ.get("VERCEL_URL", "") if os.environ.get("VERCEL_URL") else "",
]

CORS_ORIGINS = [o for o in CORS_ORIGINS if o]
