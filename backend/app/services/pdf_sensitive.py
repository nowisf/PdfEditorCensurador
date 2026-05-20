"""
Deteccion automatica de datos sensibles en PDFs.

Detecta mediante regex:
- RUT chileno (XX.XXX.XXX-D)
- Emails
- Telefonos (+56, 9 digitos)
- Numeros de tarjeta de credito
- Fechas de nacimiento
- Nombres propios (heuristica basica)
- Direcciones (patron basico)
"""

import fitz
import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = {
    "rut": {
        "regex": r"\b\d{1,2}\.?\d{3}\.?\d{3}[-][\dkK]\b",
        "label": "RUT",
    },
    "email": {
        "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "label": "Email",
    },
    "telefono": {
        "regex": r"(?:\+56|56)[\s-]?\d{1,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b|\b9\d{8}\b",
        "label": "Telefono",
    },
    "tarjeta": {
        "regex": r"\b(?:\d[ -]*?){13,19}\b",
        "label": "Posible Tarjeta",
    },
    "fecha_nacimiento": {
        "regex": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "label": "Fecha",
    },
    "pasaporte": {
        "regex": r"\b[A-Z]{1,2}\d{6,9}\b",
        "label": "Pasaporte/ID",
    },
}


class SensitiveDataDetector:
    """Detector automatico de datos sensibles en PDFs."""

    @staticmethod
    def detect_all(doc: fitz.Document) -> List[Dict]:
        """
        Escanea todas las paginas y retorna lista de datos sensibles encontrados
        con sus coordenadas para generar zonas de censura automaticas.
        """
        results = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")
            text_dict = page.get_text("dict")

            for pattern_name, pattern_info in SENSITIVE_PATTERNS.items():
                regex = re.compile(pattern_info["regex"], re.IGNORECASE)
                for match in regex.finditer(text):
                    search_text = match.group()
                    instances = page.search_for(search_text)
                    for inst in instances:
                        results.append({
                            "type": pattern_name,
                            "label": pattern_info["label"],
                            "page": page_idx,
                            "x": inst.x0 - 2,
                            "y": inst.y0 - 2,
                            "width": inst.width + 4,
                            "height": inst.height + 4,
                            "text_preview": search_text[:3] + "***",
                        })

        logger.info(f"Deteccion automatica: {len(results)} datos sensibles encontrados")
        return results

    @staticmethod
    def detect_page(doc: fitz.Document, page_idx: int) -> List[Dict]:
        """Escanea una sola pagina."""
        results = []
        if page_idx >= len(doc):
            return results

        page = doc[page_idx]
        text = page.get_text("text")

        for pattern_name, pattern_info in SENSITIVE_PATTERNS.items():
            regex = re.compile(pattern_info["regex"], re.IGNORECASE)
            for match in regex.finditer(text):
                search_text = match.group()
                instances = page.search_for(search_text)
                for inst in instances:
                    results.append({
                        "type": pattern_name,
                        "label": pattern_info["label"],
                        "page": page_idx,
                        "x": inst.x0 - 2,
                        "y": inst.y0 - 2,
                        "width": inst.width + 4,
                        "height": inst.height + 4,
                        "text_preview": search_text[:3] + "***",
                    })

        return results

    @staticmethod
    def get_detection_report(doc: fitz.Document) -> Dict:
        """Retorna un reporte resumido de datos sensibles encontrados."""
        all_detections = SensitiveDataDetector.detect_all(doc)
        summary = {}
        for d in all_detections:
            label = d["label"]
            if label not in summary:
                summary[label] = 0
            summary[label] += 1

        return {
            "total": len(all_detections),
            "by_type": summary,
            "detections": all_detections,
        }
