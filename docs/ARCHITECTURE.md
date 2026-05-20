# PDF Censura - Arquitectura del Sistema

## 1. Vision General

Sistema web de redaccion irreversible de PDFs para cumplimiento de Transparencia Activa en Chile.
La prioridad absoluta es la **seguridad e irreversibilidad** de la censura.

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ PDFViewer│  │ RedactionCanvas│  │ Toolbar/Panels   │ │
│  │ (render) │  │ (draw zones) │  │ (controls)       │ │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘ │
│       └────────────────┼──────────────────┘             │
│                   REST API                               │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP multipart
┌───────────────────────┼─────────────────────────────────┐
│               BACKEND (FastAPI + PyMuPDF)               │
│  ┌────────────────────┼────────────────────┐            │
│  │              Routes Layer                 │            │
│  │  /api/redaction/*  /api/metadata/*       │            │
│  │  /api/signature/*  /api/converter/*      │            │
│  └────────────────────┼────────────────────┘            │
│  ┌────────────────────┼────────────────────┐            │
│  │           Services Layer                  │            │
│  │  ┌─────────────┐  ┌─────────────────┐   │            │
│  │  │RedactionEngine│  │MetadataSanitizer│   │            │
│  │  │ (texto+imagen)│  │ (XMP+campos)   │   │            │
│  │  └─────────────┘  └─────────────────┘   │            │
│  │  ┌─────────────┐  ┌─────────────────┐   │            │
│  │  │PDFSignature  │  │PDFProtection    │   │            │
│  │  │ (visual+PKCS7)│ │ (AES-256+perm) │   │            │
│  │  └─────────────┘  └─────────────────┘   │            │
│  └─────────────────────────────────────────┘            │
│                     PyMuPDF (fitz)                       │
└─────────────────────────────────────────────────────────┘
```

## 2. Flujo de Censura Irreversible

### Proceso de Redaccion de Texto

```
Usuario dibuja zona → coordenadas PDF → add_redact_annot()
                                              │
                                    apply_redactions()
                                              │
                              ┌────────────────┴────────────────┐
                              │                                 │
                    Elimina operadores Tj/TJ     Reemplaza con
                    del content stream            rectangulo solido
                    (bytes destruidos)            (0,0,0 fill)
                              │
                    garbage=4, clean=True
                    (reconstruccion completa)
                              │
                    save() → PDF limpio
                    (sin historia incremental)
```

### Proceso de Saneamiento de Metadatos

```
1. Sobreescribir campos estandar → set_metadata({"author": "", ...})
2. Destruir flujo XMP             → xref_stream() → zeroed bytes
3. Eliminar referencia catalog    → xref_set_key("Metadata", "null")
4. Destruir miniaturas            → xref_set_key("Thumb", "null")
5. Eliminar PieceInfo             → xref_set_key("PieceInfo", "null")
6. Eliminar OCProperties          → xref_set_key("OCProperties", "null")
7. Limpiar propiedades custom     → regex scan + null
8. Reconstruir PDF                → save(garbage=4, clean=True)
```

## 3. Garantias de Seguridad

### Por que la censura es IRREVERSIBLE:

1. **Nivel de objetos PDF**: PyMuPDF opera directamente sobre los objetos PDF (xrefs).
   `apply_redactions()` elimina los operadores de texto del content stream, no los "tapa".

2. **Reconstruccion completa**: `save(garbage=4)` reconstruye toda la estructura del PDF
   desde cero, eliminando:
   - Objetos huerfanos
   - Actualizaciones incrementales
   - Streams comprimidos residuales
   - Historial de cambios

3. **Verificacion post-redaccion**: El motor incluye `verify_redaction()` que
   verifica mediante `get_text()` y `search_for()` que no queda texto legible.

4. **Verificacion de bytes crudos**: Los tests verifican que los bytes del archivo
   final no contienen los strings censurados.

### Que NO hace este sistema:

- NO usa overlays negros (rectangulos encima del texto)
- NO usa CSS o estilos para ocultar contenido
- NO usa anotaciones como mascara
- NO conserva versiones anteriores

## 4. Estructura del Proyecto

```
proyecto pdf censura/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Configuracion
│   │   ├── models/
│   │   │   └── schemas.py          # Modelos Pydantic
│   │   ├── services/
│   │   │   ├── pdf_redaction.py    # Motor de censura (CRITICO)
│   │   │   ├── pdf_metadata.py     # Saneamiento metadatos
│   │   │   ├── pdf_signature.py    # Firma electronica
│   │   │   └── pdf_converter.py    # Conversion formatos
│   │   └── routes/
│   │       ├── redaction.py        # Endpoints redaccion
│   │       ├── metadata.py         # Endpoints metadatos
│   │       ├── signature.py        # Endpoints firma/proteccion
│   │       └── converter.py        # Endpoints conversion
│   ├── tests/
│   │   ├── conftest.py             # Fixtures de prueba
│   │   ├── test_redaction.py       # Tests censura
│   │   └── test_metadata.py        # Tests metadatos
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Componente principal
│   │   ├── components/
│   │   │   ├── PDFViewer.jsx       # Visor + canvas de redaccion
│   │   │   ├── Toolbar.jsx         # Herramientas laterales
│   │   │   ├── MetadataPanel.jsx   # Panel de metadatos
│   │   │   └── SignaturePanel.jsx  # Panel de firma
│   │   ├── services/
│   │   │   └── api.js              # Cliente API
│   │   └── styles/
│   │       └── app.css             # Estilos
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── docs/
    └── ARCHITECTURE.md
```

## 5. API Endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/api/upload` | Subir PDF y obtener info |
| POST | `/api/redaction/render-page` | Renderizar pagina como imagen |
| POST | `/api/redaction/page-info` | Dimensiones de paginas |
| POST | `/api/redaction/apply-redaction` | **Aplicar censura irreversible** |
| POST | `/api/redaction/extract-text` | Extraer texto (verificacion) |
| POST | `/api/metadata/inspect` | Inspeccionar metadatos |
| POST | `/api/metadata/sanitize` | **Destruir metadatos** |
| POST | `/api/signature/visual-signature` | Firma visual |
| POST | `/api/signature/protect` | Encriptar PDF |
| POST | `/api/converter/images-to-pdf` | Imagenes a PDF |
| POST | `/api/converter/pdf-to-images` | PDF a imagenes |
| POST | `/api/converter/merge` | Combinar PDFs |

## 6. Ejecucion

### Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend:
```bash
cd frontend
npm install
npm run dev
```

### Tests:
```bash
cd backend
pytest tests/ -v
```

## 7. Tecnologias Clave

| Componente | Tecnologia | Razon |
|-----------|-----------|-------|
| Backend | Python 3.11+ / FastAPI | Async, tipos, docs automaticas |
| Motor PDF | PyMuPDF (fitz) | Redaccion nativa a nivel objetos |
| Frontend | React 18 + Vite | Rendimiento, ecosistema |
| Imagenes | Pillow + NumPy | Manipulacion pixel-level |
| Criptografia | cryptography (Python) | AES-256, PKCS#7 |
| Validacion | Pydantic v2 | Schemas tipados |
