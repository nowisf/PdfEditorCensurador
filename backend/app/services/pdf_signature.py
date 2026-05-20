"""
Modulo de Firma Electronica y Proteccion de PDF.

Implementa:
- Firma digital criptografica (PKCS#7) sobre PDF
- Firma visual (imagen + texto en zona designada)
- Encriptacion AES-256 con permisos granulares
"""

import fitz
import io
import hashlib
import os
from datetime import datetime
from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import load_pem_x509_certificate
from ..models.schemas import ProtectionOptions, SignaturePosition

import logging

logger = logging.getLogger(__name__)


class PDFSignature:
    """Manejador de firmas electronicas en PDF."""

    @staticmethod
    def add_visual_signature(
        doc: fitz.Document,
        position: SignaturePosition,
        signer_name: str = "",
        signer_rut: str = "",
        reason: str = "Firma para Transparencia Activa",
        image_path: Optional[str] = None,
        include_hash: bool = True,
        include_box: bool = True,
    ) -> fitz.Document:
        if position.page >= len(doc):
            raise ValueError(f"Pagina {position.page} fuera de rango")

        page = doc[position.page]

        doc_hash = PDFSignature._compute_document_hash(doc) if include_hash else None
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        font_size = 7
        line_height = font_size + 3
        padding = 8

        lines = [
            f"Firmado por: {signer_name}",
            f"RUT: {signer_rut}",
            f"Fecha: {timestamp}",
            f"Motivo: {reason}",
        ]

        if include_hash and doc_hash:
            lines.append(f"SHA-256: {doc_hash[:32]}")
            lines.append(f"         {doc_hash[32:]}")

        text_height = padding + len(lines) * line_height + padding

        rect = fitz.Rect(
            position.x, position.y,
            position.x + position.width,
            position.y + max(position.height, text_height),
        )

        shape = page.new_shape()
        if include_box:
            shape.draw_rect(rect)
            shape.finish(color=(0, 0, 0.6), width=1.5)

        text_x = rect.x0 + padding
        text_y = rect.y0 + padding + font_size

        for line in lines:
            shape.insert_text(
                fitz.Point(text_x, text_y),
                line,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0),
            )
            text_y += line_height

        shape.commit()
        logger.info(f"Firma visual agregada en pagina {position.page}")
        return doc

    @staticmethod
    def sign_digital(
        doc: fitz.Document,
        p12_path: str,
        p12_password: str,
        position: SignaturePosition,
        signer_name: str = "",
        reason: str = "Firma digital para Transparencia Activa",
    ) -> fitz.Document:
        """
        Agrega firma digital criptografica PKCS#7 al PDF.
        
        Utiliza un certificado .p12/.pfx para crear una firma
        criptograficamente valida segun estandar PDF Signature.
        """
        if position.page >= len(doc):
            raise ValueError(f"Pagina {position.page} fuera de rango")

        page = doc[position.page]
        rect = fitz.Rect(
            position.x, position.y,
            position.x + position.width,
            position.y + position.height,
        )

        timestamp = datetime.now().strftime("D:%Y%m%d%H%M%S+03'00'")

        signature_widget = {
            "sigflags": 3,
            "sigdate": timestamp,
            "signature": signer_name,
            "reason": reason,
            "contact": signer_name,
            "location": "Chile",
        }

        try:
            doc.insert_signature(
                signature_widget,
                certificate=p12_path,
                password=p12_password.encode() if isinstance(p12_password, str) else p12_password,
            )
            logger.info("Firma digital PKCS#7 aplicada")
        except Exception as e:
            raise RuntimeError(
                f"Firma digital PKCS#7 fallida: {e}. "
                f"Verifique que el certificado sea valido, la contrasena sea correcta "
                f"y el formato sea .p12/.pfx emitido por una CA reconocida."
            ) from e

        return doc

    @staticmethod
    def _compute_document_hash(doc: fitz.Document) -> str:
        """Computa hash SHA-256 del contenido del documento para integridad."""
        buf = io.BytesIO()
        doc.save(buf, garbage=3, clean=True)
        return hashlib.sha256(buf.getvalue()).hexdigest()


class PDFProtection:
    """Manejador de proteccion y encriptacion de PDF."""

    @staticmethod
    def apply_protection(
        doc: fitz.Document,
        options: ProtectionOptions,
    ) -> bytes:
        """
        Aplica encriptacion y permisos al PDF.
        
        Retorna los bytes del PDF protegido con AES-256.
        Permisos granulares: impresion, copia, modificacion, anotaciones.
        """
        perm = 0
        if options.allow_print:
            perm |= fitz.PDF_PERM_PRINT
        if options.allow_copy:
            perm |= fitz.PDF_PERM_COPY
        if options.allow_modify:
            perm |= fitz.PDF_PERM_MODIFY
        if options.allow_annotate:
            perm |= fitz.PDF_PERM_ANNOTATE

        buf = io.BytesIO()
        doc.save(
            buf,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=options.owner_password or "",
            user_pw=options.user_password or "",
            permissions=perm,
            garbage=4,
            clean=True,
        )

        logger.info("Proteccion AES-256 aplicada al PDF")
        return buf.getvalue()

    @staticmethod
    def save_protected(
        doc: fitz.Document,
        output_path: str,
        options: ProtectionOptions,
    ):
        """Guarda el PDF con proteccion aplicada."""
        perm = 0
        if options.allow_print:
            perm |= fitz.PDF_PERM_PRINT
        if options.allow_copy:
            perm |= fitz.PDF_PERM_COPY
        if options.allow_modify:
            perm |= fitz.PDF_PERM_MODIFY
        if options.allow_annotate:
            perm |= fitz.PDF_PERM_ANNOTATE

        doc.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=options.owner_password or "",
            user_pw=options.user_password or "",
            permissions=perm,
            garbage=4,
            clean=True,
            deflate=True,
        )
        logger.info(f"PDF protegido guardado en {output_path}")
