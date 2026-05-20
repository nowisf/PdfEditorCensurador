import { useState, useRef } from 'react'
import * as api from '../services/api'

export default function Toolbar({
  redactionMode,
  setRedactionMode,
  redactionZones,
  onRemoveZone,
  onApplyRedaction,
  loading,
  setLoading,
  pdfFile,
  activePanel,
  setActivePanel,
  onSanitizeMetadata,
  onApplyResult,
  onUndo,
  onRedo,
  onClearAll,
  canUndo,
  canRedo,
  textZone,
  onSetTextZone,
  textPreview,
  onSetTextPreview,
}) {
  const modes = [
    { id: 'select', label: 'Seleccionar', icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z" />
      </svg>
    )},
    { id: 'text', label: 'Censura Texto', icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 7V4h16v3" /><path d="M9 20h6" /><path d="M12 4v16" />
      </svg>
    )},
    { id: 'image', label: 'Censura Imagen', icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />
      </svg>
    )},
    { id: 'region', label: 'Censura Region', icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" />
      </svg>
    )},
  ]

  const panels = [
    { id: 'redaction', label: 'Censura' },
    { id: 'metadata', label: 'Metadatos' },
    { id: 'signature', label: 'Firma' },
    { id: 'convert', label: 'Convertir' },
    { id: 'verify', label: 'Verificar' },
    { id: 'detect', label: 'Detectar' },
    { id: 'pages', label: 'Paginas' },
    { id: 'text', label: 'Texto' },
    { id: 'watermark', label: 'Marca' },
    { id: 'audit', label: 'Audit' },
  ]

  return (
    <div className="toolbar">
      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Panel</h3>
        <div className="panel-tabs">
          {panels.map((p) => (
            <button
              key={p.id}
              className={`panel-tab ${activePanel === p.id ? 'active' : ''}`}
              onClick={() => setActivePanel(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {activePanel === 'redaction' && (
        <>
          <div className="toolbar-section">
            <h3 className="toolbar-section-title">Herramienta</h3>
            <div className="tool-grid">
              {modes.map((mode) => (
                <button
                  key={mode.id}
                  className={`tool-btn ${redactionMode === mode.id ? 'active' : ''}`}
                  onClick={() => setRedactionMode(mode.id)}
                  title={mode.label}
                >
                  {mode.icon}
                  <span>{mode.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="toolbar-section">
            <h3 className="toolbar-section-title">
              Zonas de Censura
              <span className="zone-count">{redactionZones.length}</span>
            </h3>
            <div className="zone-actions">
              <button className="btn btn-sm" disabled={!canUndo} onClick={onUndo} title="Deshacer (Ctrl+Z)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 105.64-11.36L1 10" /></svg>
              </button>
              <button className="btn btn-sm" disabled={!canRedo} onClick={onRedo} title="Rehacer (Ctrl+Y)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 11-5.64-11.36L23 10" /></svg>
              </button>
              <button className="btn btn-sm" disabled={redactionZones.length === 0} onClick={onClearAll} title="Limpiar todo (Delete)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" /></svg>
                Limpiar
              </button>
            </div>
            {redactionZones.length === 0 ? (
              <p className="empty-zones">Dibuje zonas sobre el PDF para marcar areas a censurar</p>
            ) : (
              <div className="zone-list">
                {redactionZones.map((zone, idx) => (
                  <div key={idx} className={`zone-item zone-item-${zone.redaction_type}`}>
                    <div className="zone-item-info">
                      <span className="zone-item-type">
                        {zone.redaction_type === 'text' ? 'TEXTO' : zone.redaction_type === 'image' ? 'IMAGEN' : 'REGION'}
                      </span>
                      <span className="zone-item-page">Pag. {zone.page + 1}</span>
                    </div>
                    <button className="zone-item-remove" onClick={() => onRemoveZone(idx)}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="toolbar-section toolbar-actions">
            <button
              className="btn btn-danger btn-full"
              disabled={!pdfFile || redactionZones.length === 0 || loading}
              onClick={onApplyRedaction}
            >
              {loading ? (
                <span className="spinner" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              )}
              {loading ? 'Procesando...' : 'Aplicar Censura Irreversible'}
            </button>
            <p className="action-warning">
              Esta accion destruye la informacion de forma permanente e irreversible.
            </p>
          </div>
        </>
      )}

      {activePanel === 'metadata' && (
        <div className="toolbar-section">
          <h3 className="toolbar-section-title">Saneamiento</h3>
          <p className="section-desc">
            Destruye todos los metadatos del PDF: autor, creador, fechas, historial, miniaturas y datos XML/XMP ocultos.
          </p>
          <button
            className="btn btn-danger btn-full"
            disabled={!pdfFile || loading}
            onClick={onSanitizeMetadata}
          >
            Destruir Metadatos
          </button>
        </div>
      )}

      {activePanel === 'signature' && (
        <div className="toolbar-section">
          <h3 className="toolbar-section-title">Firma Electronica</h3>
          <p className="section-desc">
            Funciones de firma disponibles en el panel derecho.
          </p>
        </div>
      )}

      {activePanel === 'convert' && (
        <ConvertPanel pdfFile={pdfFile} loading={loading} setLoading={setLoading} onApplyResult={onApplyResult} />
      )}

      {activePanel === 'verify' && (
        <VerifyPanel pdfFile={pdfFile} loading={loading} setLoading={setLoading} />
      )}

      {activePanel === 'detect' && (
        <DetectPanel pdfFile={pdfFile} loading={loading} setLoading={setLoading} onApplyResult={onApplyResult} />
      )}

      {activePanel === 'pages' && (
        <PagesPanel pdfFile={pdfFile} loading={loading} setLoading={setLoading} onApplyResult={onApplyResult} />
      )}

      {activePanel === 'text' && (
        <TextPanel pdfFile={pdfFile} loading={loading} setLoading={setLoading} onApplyResult={onApplyResult} textZone={textZone} onSetTextZone={onSetTextZone} textPreview={textPreview} onSetTextPreview={onSetTextPreview} />
      )}

      {activePanel === 'watermark' && (
        <WatermarkPanel pdfFile={pdfFile} loading={loading} setLoading={setLoading} onApplyResult={onApplyResult} />
      )}

      {activePanel === 'audit' && (
        <AuditPanel />
      )}
    </div>
  )
}

function ConvertPanel({ pdfFile, loading, setLoading, onApplyResult }) {
  const [imgFiles, setImgFiles] = useState([])
  const [pdfFiles, setPdfFiles] = useState([])
  const imgInputRef = useRef(null)
  const pdfMergeRef = useRef(null)

  const handleImagesToPdf = async () => {
    if (imgFiles.length === 0) return
    setLoading(true)
    try {
      const formData = new FormData()
      imgFiles.forEach((f) => formData.append('files', f))
      const resp = await fetch('/api/converter/images-to-pdf', { method: 'POST', body: formData })
      const blob = await resp.blob()
      const file = new File([blob], 'convertido.pdf', { type: 'application/pdf' })
      if (onApplyResult) {
        await onApplyResult(blob, 'convertido.pdf')
      } else {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'convertido.pdf'
        a.click()
      }
      setImgFiles([])
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handlePdfToImages = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', pdfFile)
      formData.append('dpi', '200')
      const resp = await fetch('/api/converter/pdf-to-images', { method: 'POST', body: formData })
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'paginas.zip'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleMergePdfs = async () => {
    if (pdfFiles.length < 2) return
    setLoading(true)
    try {
      const formData = new FormData()
      pdfFiles.forEach((f) => formData.append('files', f))
      const resp = await fetch('/api/converter/merge', { method: 'POST', body: formData })
      const blob = await resp.blob()
      if (onApplyResult) {
        await onApplyResult(blob, 'combinado.pdf')
      } else {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'combinado.pdf'
        a.click()
      }
      setPdfFiles([])
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Imagenes a PDF</h3>
        <p className="section-desc">Convierta imagenes PNG, JPEG, TIFF en un documento PDF.</p>
        <button className="btn btn-sm btn-full" onClick={() => imgInputRef.current?.click()}>
          Seleccionar imagenes ({imgFiles.length})
        </button>
        <input
          ref={imgInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => setImgFiles(Array.from(e.target.files || []))}
          style={{ display: 'none' }}
        />
        <button
          className="btn btn-primary btn-full"
          style={{ marginTop: 8 }}
          disabled={imgFiles.length === 0 || loading}
          onClick={handleImagesToPdf}
        >
          {loading ? 'Convirtiendo...' : 'Convertir a PDF'}
        </button>
      </div>

      <div className="toolbar-section">
        <h3 className="toolbar-section-title">PDF a Imagenes</h3>
        <p className="section-desc">Exporte cada pagina del PDF como imagen PNG.</p>
        <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handlePdfToImages}>
          {loading ? 'Exportando...' : 'Exportar paginas como PNG'}
        </button>
      </div>

      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Combinar PDFs</h3>
        <p className="section-desc">Una multiples PDFs en un solo documento.</p>
        <button className="btn btn-sm btn-full" onClick={() => pdfMergeRef.current?.click()}>
          Seleccionar PDFs ({pdfFiles.length})
        </button>
        <input
          ref={pdfMergeRef}
          type="file"
          accept=".pdf"
          multiple
          onChange={(e) => setPdfFiles(Array.from(e.target.files || []))}
          style={{ display: 'none' }}
        />
        <button
          className="btn btn-primary btn-full"
          style={{ marginTop: 8 }}
          disabled={pdfFiles.length < 2 || loading}
          onClick={handleMergePdfs}
        >
          {loading ? 'Combinando...' : 'Combinar PDFs'}
        </button>
      </div>
    </>
  )
}

function VerifyPanel({ pdfFile, loading, setLoading }) {
  const [extractedText, setExtractedText] = useState('')
  const [verifyPage, setVerifyPage] = useState(0)

  const handleExtract = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const data = await api.extractText(pdfFile, verifyPage)
      setExtractedText(data.text || '(sin texto)')
    } catch (err) {
      setExtractedText('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="toolbar-section">
      <h3 className="toolbar-section-title">Verificacion de Texto</h3>
      <p className="section-desc">
        Extraiga el texto del PDF para verificar que la informacion censurada ya no es recuperable.
      </p>
      <div className="form-group">
        <label>Pagina</label>
        <input
          type="number"
          value={verifyPage}
          onChange={(e) => setVerifyPage(parseInt(e.target.value) || 0)}
          min="0"
        />
      </div>
      <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleExtract}>
        {loading ? 'Extrayendo...' : 'Extraer Texto'}
      </button>
      {extractedText && (
        <div className="verify-result">
          <h4 className="toolbar-section-title" style={{ marginTop: 12 }}>Texto Extraido</h4>
          <pre className="verify-text">{extractedText}</pre>
        </div>
      )}
    </div>
  )
}

function DetectPanel({ pdfFile, loading, setLoading, onApplyResult }) {
  const [report, setReport] = useState(null)

  const handleDetect = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const data = await api.detectSensitive(pdfFile)
      setReport(data)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAutoRedact = () => {
    if (!report || !onApplyResult) return
    const zones = report.detections.map((d) => ({
      page: d.page,
      x: d.x,
      y: d.y,
      width: d.width,
      height: d.height,
      redaction_type: 'text',
      color: [0, 0, 0],
      fill: true,
    }))
    alert(`${zones.length} zonas detectadas. Use el panel de Censura para aplicarlas.`)
  }

  return (
    <div className="toolbar-section">
      <h3 className="toolbar-section-title">Deteccion Automatica</h3>
      <p className="section-desc">Busca RUTs, emails, telefonos y otros datos sensibles.</p>
      <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleDetect}>
        {loading ? 'Escaneando...' : 'Escanear Datos Sensibles'}
      </button>
      {report && (
        <div className="detect-results">
          <div className="detect-summary">
            <span className="detect-total">{report.total} datos encontrados</span>
          </div>
          {Object.entries(report.by_type).map(([type, count]) => (
            <div key={type} className="detect-row">
              <span className="detect-type">{type}</span>
              <span className="detect-count">{count}</span>
            </div>
          ))}
          {report.total > 0 && (
            <button className="btn btn-danger btn-full" style={{ marginTop: 8 }} onClick={handleAutoRedact}>
              Usar como zonas de censura
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function PagesPanel({ pdfFile, loading, setLoading, onApplyResult }) {
  const [rotateDeg, setRotateDeg] = useState(90)
  const [deletePagesInput, setDeletePagesInput] = useState('')
  const [addCount, setAddCount] = useState(1)
  const [addPosition, setAddPosition] = useState('end')
  const [addWidth, setAddWidth] = useState(612)
  const [addHeight, setAddHeight] = useState(792)
  const [addContent, setAddContent] = useState('')

  const handleRotate = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const blob = await api.rotatePages(pdfFile, [], rotateDeg)
      await onApplyResult(blob, `rotated_${pdfFile.name}`)
    } catch (err) { alert('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleDelete = async () => {
    if (!pdfFile || !deletePagesInput) return
    const pages = deletePagesInput.split(',').map((s) => parseInt(s.trim())).filter((n) => !isNaN(n))
    if (pages.length === 0) return
    setLoading(true)
    try {
      const blob = await api.deletePages(pdfFile, pages)
      await onApplyResult(blob, `edited_${pdfFile.name}`)
      setDeletePagesInput('')
    } catch (err) { alert('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleAddPages = async () => {
    if (!pdfFile || addCount < 1) return
    setLoading(true)
    try {
      const blob = await api.addPages(pdfFile, addCount, addPosition, addWidth, addHeight, addContent)
      await onApplyResult(blob, `pages_added_${pdfFile.name}`)
    } catch (err) { alert('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  return (
    <>
      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Agregar Paginas</h3>
        <div className="form-group">
          <label>Cantidad</label>
          <input type="number" value={addCount} onChange={(e) => setAddCount(Math.max(1, parseInt(e.target.value) || 1))} min="1" max="100" />
        </div>
        <div className="form-group">
          <label>Posicion</label>
          <select value={addPosition} onChange={(e) => setAddPosition(e.target.value)} className="form-select">
            <option value="end">Al final</option>
            <option value="start">Al inicio</option>
          </select>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Ancho (pt)</label>
            <select value={`${addWidth},${addHeight}`} onChange={(e) => {
              const [w, h] = e.target.value.split(',').map(Number)
              setAddWidth(w)
              setAddHeight(h)
            }} className="form-select">
              <option value="612,792">Letter (612x792)</option>
              <option value="595,842">A4 (595x842)</option>
              <option value="612,1008">Legal (612x1008)</option>
              <option value="522,756">Ejecutivo (522x756)</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Contenido (opcional)</label>
          <textarea
            value={addContent}
            onChange={(e) => setAddContent(e.target.value)}
            placeholder="Dejar vacio para pagina en blanco"
            rows={3}
            className="form-textarea"
          />
        </div>
        <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleAddPages}>
          {loading ? 'Agregando...' : `Agregar ${addCount} pagina${addCount > 1 ? 's' : ''}`}
        </button>
      </div>

      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Rotar Paginas</h3>
        <div className="form-row">
          <select value={rotateDeg} onChange={(e) => setRotateDeg(parseInt(e.target.value))} className="form-select">
            <option value={0}>0° (Original)</option>
            <option value={90}>90°</option>
            <option value={180}>180°</option>
            <option value={270}>270°</option>
          </select>
          <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleRotate}>
            {loading ? 'Rotando...' : 'Rotar todo'}
          </button>
        </div>
      </div>
      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Eliminar Paginas</h3>
        <p className="section-desc">Ingrese numeros separados por coma (ej: 0,2,5)</p>
        <div className="form-group">
          <input
            type="text"
            value={deletePagesInput}
            onChange={(e) => setDeletePagesInput(e.target.value)}
            placeholder="0,2,5"
          />
        </div>
        <button className="btn btn-danger btn-full" disabled={!pdfFile || !deletePagesInput || loading} onClick={handleDelete}>
          {loading ? 'Eliminando...' : 'Eliminar paginas'}
        </button>
      </div>
    </>
  )
}

function WatermarkPanel({ pdfFile, loading, setLoading, onApplyResult }) {
  const [wmText, setWmText] = useState('CONFIDENCIAL')
  const [wmAngle, setWmAngle] = useState(45)
  const [wmFontsize, setWmFontsize] = useState(60)
  const [stampText, setStampText] = useState('CENSURADO')

  const handleWatermark = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const blob = await api.applyWatermark(pdfFile, wmText, 0.15, wmFontsize, wmAngle)
      await onApplyResult(blob, `wm_${pdfFile.name}`)
    } catch (err) { alert('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const handleStamp = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const blob = await api.applyStamp(pdfFile, stampText)
      await onApplyResult(blob, `stamped_${pdfFile.name}`)
    } catch (err) { alert('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  return (
    <>
      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Marca de Agua</h3>
        <p className="section-desc">Texto rotado semitransparente en todas las paginas.</p>
        <div className="form-group">
          <label>Texto</label>
          <input type="text" value={wmText} onChange={(e) => setWmText(e.target.value)} />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Angulo</label>
            <input type="number" value={wmAngle} onChange={(e) => setWmAngle(parseInt(e.target.value) || 0)} min="-90" max="90" />
          </div>
          <div className="form-group">
            <label>Tamano</label>
            <input type="number" value={wmFontsize} onChange={(e) => setWmFontsize(parseInt(e.target.value) || 60)} min="10" max="200" />
          </div>
        </div>
        <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleWatermark}>
          {loading ? 'Aplicando...' : 'Aplicar marca de agua'}
        </button>
      </div>
      <div className="toolbar-section">
        <h3 className="toolbar-section-title">Sello</h3>
        <p className="section-desc">Texto con fecha en la esquina superior.</p>
        <div className="form-group">
          <label>Texto del sello</label>
          <input type="text" value={stampText} onChange={(e) => setStampText(e.target.value)} />
        </div>
        <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleStamp}>
          {loading ? 'Aplicando...' : 'Aplicar sello'}
        </button>
      </div>
    </>
  )
}

function AuditPanel() {
  const [logs, setLogs] = useState(null)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.getAuditStats().then(setStats).catch(() => {})
    api.getAuditLogs(null, 50).then((data) => setLogs(data.logs)).catch(() => {})
  }, [])

  return (
    <div className="toolbar-section">
      <h3 className="toolbar-section-title">Auditoria</h3>
      {stats && (
        <div className="audit-stats">
          <div className="detect-row"><span className="detect-type">Total operaciones</span><span className="detect-count">{stats.total_operations}</span></div>
          {Object.entries(stats.by_type).map(([op, count]) => (
            <div key={op} className="detect-row"><span className="detect-type">{op}</span><span className="detect-count">{count}</span></div>
          ))}
        </div>
      )}
      {logs && logs.length > 0 && (
        <div className="audit-log-list">
          <h4 className="toolbar-section-title" style={{ marginTop: 12 }}>Recientes</h4>
          {logs.slice(-10).reverse().map((log, i) => (
            <div key={i} className="audit-entry">
              <span className="audit-op">{log.operation}</span>
              <span className="audit-time">{new Date(log.timestamp).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
      {(!logs || logs.length === 0) && <p className="section-desc">No hay operaciones registradas.</p>}
    </div>
  )
}

function TextPanel({ pdfFile, loading, setLoading, onApplyResult, textZone, onSetTextZone, textPreview, onSetTextPreview }) {
  const [customFont, setCustomFont] = useState(null)

  const BUILTIN_FONTS = [
    { id: 'helv', label: 'Helvetica', css: 'Helvetica, Arial, sans-serif' },
    { id: 'cour', label: 'Courier', css: '"Courier New", Courier, monospace' },
    { id: 'tiro', label: 'Times Roman', css: '"Times New Roman", Times, serif' },
    { id: 'symb', label: 'Symbol', css: 'Symbol' },
    { id: 'zadb', label: 'Zapf Dingbats', css: '"Zapf Dingbats"' },
  ]

  const currentFont = BUILTIN_FONTS.find((f) => f.id === textPreview.font)

  const handleFontUpload = (e) => {
    const f = e.target.files?.[0]
    if (f) {
      setCustomFont(f)
      onSetTextPreview({ ...textPreview, font: 'custom' })
    }
  }

  const handleSubmit = async () => {
    if (!pdfFile || !textPreview.content) {
      alert('Dibuje una zona en el visor y escriba el texto')
      return
    }
    if (!textZone) {
      alert('Dibuje una zona en el visor primero')
      return
    }
    setLoading(true)
    try {
      const blob = await api.addText(
        pdfFile,
        textZone.page, textZone.x, textZone.y, textZone.width, textZone.height,
        textPreview.content, textPreview.fontSize, textPreview.align,
        textPreview.font === 'custom' ? customFont : null,
        textPreview.font !== 'custom' ? textPreview.font : 'customfont'
      )
      await onApplyResult(blob, `text_${pdfFile.name}`)
      onSetTextPreview({ content: '', fontSize: 12, align: 0, font: 'helv' })
      onSetTextZone(null)
      setCustomFont(null)
    } catch (err) { alert('Error: ' + err.message) }
    finally { setLoading(false) }
  }

  const cssFont = textPreview.font === 'custom' && customFont
    ? customFont.name.replace(/\.(ttf|otf)$/i, '')
    : currentFont?.css || 'Helvetica, Arial, sans-serif'

  return (
    <div className="toolbar-section">
      <h3 className="toolbar-section-title">Insertar Texto</h3>
      <p className="section-desc">
        Dibuje una zona en el visor donde quiere insertar texto, luego complete los campos.
      </p>
      <div className="form-group">
        <label>Fuente</label>
        <select
          value={textPreview.font === 'custom' ? '__custom' : textPreview.font}
          onChange={(e) => {
            if (e.target.value !== '__custom') {
              onSetTextPreview({ ...textPreview, font: e.target.value })
              setCustomFont(null)
            }
          }}
          className="form-select"
        >
          {BUILTIN_FONTS.map((f) => (
            <option key={f.id} value={f.id}>{f.label}</option>
          ))}
          {customFont && <option value="__custom">Custom: {customFont.name}</option>}
        </select>
      </div>
      <div className="form-group">
        <label>Cargar fuente TTF/OTF</label>
        <div className="font-upload-row">
          <label className="btn btn-sm btn-secondary font-upload-btn">
            Elegir archivo
            <input type="file" accept=".ttf,.otf" onChange={handleFontUpload} style={{ display: 'none' }} />
          </label>
          {customFont && <span className="font-filename">{customFont.name}</span>}
        </div>
      </div>
      <div className="form-group">
        <label>Texto</label>
        <textarea
          value={textPreview.content}
          onChange={(e) => onSetTextPreview({ ...textPreview, content: e.target.value })}
          placeholder="Escriba el texto a insertar..."
          rows={4}
          className="form-textarea"
          style={{ fontFamily: cssFont, fontSize: Math.min(textPreview.fontSize, 18) }}
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Tamano</label>
          <input type="number" value={textPreview.fontSize} onChange={(e) => onSetTextPreview({ ...textPreview, fontSize: parseInt(e.target.value) || 12 })} min="6" max="72" />
        </div>
        <div className="form-group">
          <label>Alineacion</label>
          <select value={textPreview.align} onChange={(e) => onSetTextPreview({ ...textPreview, align: parseInt(e.target.value) })} className="form-select">
            <option value={0}>Izquierda</option>
            <option value={1}>Centro</option>
            <option value={2}>Derecha</option>
          </select>
        </div>
      </div>
      {textZone ? (
        <p className="sig-position-set" style={{ marginBottom: 8 }}>
          Zona definida en Pag. {textZone.page + 1}
        </p>
      ) : (
        <p className="sig-position-hint" style={{ marginBottom: 8 }}>
          Dibuje una zona en el visor primero
        </p>
      )}
      <button className="btn btn-primary btn-full" disabled={!pdfFile || !textPreview.content || !textZone || loading} onClick={handleSubmit}>
        {loading ? 'Insertando...' : 'Insertar texto'}
      </button>
    </div>
  )
}
