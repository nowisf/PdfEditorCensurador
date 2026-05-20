import os
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import json

from ..models.schemas import SignaturePosition, ProtectionOptions
from ..services.pdf_signature import PDFSignature, PDFProtection
from ..config import UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signature", tags=["Firma y Proteccion"])


@router.post("/visual-signature")
async def add_visual_signature(
    file: UploadFile = File(...),
    position_json: str = Form(...),
    signer_name: str = Form(""),
    signer_rut: str = Form(""),
    reason: str = Form("Firma para Transparencia Activa"),
    include_hash: str = Form("true"),
    include_box: str = Form("true"),
):
    """Agrega firma visual con hash de integridad al PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        pos_data = json.loads(position_json)
        position = SignaturePosition(**pos_data)
    except Exception as e:
        raise HTTPException(400, f"Posicion invalida: {str(e)}")

    try:
        import fitz
        doc = fitz.open(tmp_path)
        PDFSignature.add_visual_signature(
            doc, position,
            signer_name=signer_name,
            signer_rut=signer_rut,
            reason=reason,
            include_hash=include_hash.lower() in ("true", "1", "yes"),
            include_box=include_box.lower() in ("true", "1", "yes"),
        )

        output_filename = f"SIGNED_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
        )
    except Exception as e:
        raise HTTPException(500, f"Error firmando PDF: {str(e)}")


@router.post("/digital-signature")
async def digital_signature(
    file: UploadFile = File(...),
    certificate: UploadFile = File(...),
    cert_password: str = Form(""),
    position_json: str = Form(...),
    signer_name: str = Form(""),
    reason: str = Form("Firma digital para Transparencia Activa"),
):
    """Agrega firma digital PKCS#7 usando certificado .p12/.pfx."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    cert_ext = certificate.filename.lower()
    if not (cert_ext.endswith(".p12") or cert_ext.endswith(".pfx")):
        raise HTTPException(400, "El certificado debe ser .p12 o .pfx")

    cert_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{certificate.filename}")
    cert_content = await certificate.read()
    with open(cert_path, "wb") as f:
        f.write(cert_content)

    try:
        pos_data = json.loads(position_json)
        position = SignaturePosition(**pos_data)
    except Exception as e:
        raise HTTPException(400, f"Posicion invalida: {str(e)}")

    try:
        import fitz
        doc = fitz.open(tmp_path)
        PDFSignature.sign_digital(
            doc, cert_path, cert_password, position,
            signer_name=signer_name, reason=reason,
        )

        output_filename = f"DIGISIGNED_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        try:
            os.unlink(cert_path)
        except Exception:
            pass

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
        )
    except Exception as e:
        try:
            os.unlink(cert_path)
        except Exception:
            pass
        raise HTTPException(500, f"Error firmando digitalmente: {str(e)}")


@router.post("/protect")
async def protect_pdf(
    file: UploadFile = File(...),
    options_json: str = Form(...),
):
    """Aplica encriptacion AES-256 y permisos al PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        opts_data = json.loads(options_json)
        options = ProtectionOptions(**opts_data)
    except Exception as e:
        raise HTTPException(400, f"Opciones de proteccion invalidas: {str(e)}")

    try:
        import fitz
        doc = fitz.open(tmp_path)

        output_filename = f"PROTECTED_{uuid.uuid4().hex}_{file.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        PDFProtection.save_protected(doc, output_path, options)
        doc.close()

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=output_filename,
        )
    except Exception as e:
        raise HTTPException(500, f"Error protegiendo PDF: {str(e)}")
