"""
Registro de auditoria para operaciones del sistema.

Registra todas las operaciones realizadas sobre PDFs para cumplimiento
de Transparencia Activa y trazabilidad.
"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

AUDIT_LOG_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "pdf_censura_audit")
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)


class AuditLogger:
    """Registro inmutable de operaciones."""

    @staticmethod
    def log_operation(
        operation: str,
        filename: str = "",
        details: Optional[Dict] = None,
        user: str = "anonymous",
        success: bool = True,
    ) -> Dict:
        """Registra una operacion en el log de auditoria."""
        entry = {
            "id": uuid.uuid4().hex[:12],
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "filename": filename,
            "user": user,
            "success": success,
            "details": details or {},
        }

        log_path = os.path.join(
            AUDIT_LOG_DIR,
            f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl",
        )

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(f"Audit: {operation} on {filename} by {user}")
        return entry

    @staticmethod
    def get_logs(date: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Lee los logs de auditoria."""
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        log_path = os.path.join(AUDIT_LOG_DIR, f"audit_{date}.jsonl")
        if not os.path.exists(log_path):
            return []

        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        return entries[-limit:]

    @staticmethod
    def get_stats() -> Dict:
        """Retorna estadisticas de operaciones."""
        all_logs = []
        if os.path.exists(AUDIT_LOG_DIR):
            for fname in os.listdir(AUDIT_LOG_DIR):
                if fname.startswith("audit_") and fname.endswith(".jsonl"):
                    fpath = os.path.join(AUDIT_LOG_DIR, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                all_logs.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                continue

        stats = {
            "total_operations": len(all_logs),
            "by_type": {},
            "recent": all_logs[-10:] if all_logs else [],
        }
        for entry in all_logs:
            op = entry.get("operation", "unknown")
            stats["by_type"][op] = stats["by_type"].get(op, 0) + 1

        return stats
