import { useState, useRef, useCallback, useEffect } from 'react'
import PDFViewer from './components/PDFViewer'
import Toolbar from './components/Toolbar'
import MetadataPanel from './components/MetadataPanel'
import SignaturePanel from './components/SignaturePanel'
import * as api from './services/api'

export default function App() {
  const [pdfFile, setPdfFile] = useState(null)
  const [pdfInfo, setPdfInfo] = useState(null)
  const [currentPage, setCurrentPage] = useState(0)
  const [redactionZones, setRedactionZones] = useState([])
  const [undoStack, setUndoStack] = useState([])
  const [redoStack, setRedoStack] = useState([])
  const [isDrawing, setIsDrawing] = useState(false)
  const [redactionMode, setRedactionMode] = useState('text')
  const [loading, setLoading] = useState(false)
  const [activePanel, setActivePanel] = useState('redaction')
  const [statusMessage, setStatusMessage] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [resultBlobUrl, setResultBlobUrl] = useState(null)
  const [signatureZone, setSignatureZone] = useState(null)
  const [textZone, setTextZone] = useState(null)
  const [textPreview, setTextPreview] = useState({ content: '', fontSize: 12, align: 0, font: 'helv' })
  const fileInputRef = useRef(null)
  const dragCounter = useRef(0)

  const processFile = useCallback(async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setStatusMessage({ type: 'error', text: 'Solo se aceptan archivos PDF' })
      return
    }
    setPdfFile(file)
    setRedactionZones([])
    setUndoStack([])
    setRedoStack([])
    setSignatureZone(null)
    setTextZone(null)
    setStatusMessage(null)
    try {
      const info = await api.uploadPDF(file)
      setPdfInfo(info)
      setStatusMessage({ type: 'success', text: `PDF cargado: ${info.pages} paginas` })
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Error al cargar PDF: ${err.message}` })
    }
  }, [])

  const handleFileUpload = useCallback((e) => {
    processFile(e.target.files?.[0])
  }, [processFile])

  const handleDragEnter = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.current += 1
    if (dragCounter.current === 1) setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.current -= 1
    if (dragCounter.current === 0) setIsDragOver(false)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter.current = 0
    setIsDragOver(false)
    const file = e.dataTransfer?.files?.[0]
    processFile(file)
  }, [processFile])

  const handleAddZone = useCallback((zone) => {
    const newZone = { ...zone, page: zone.page ?? currentPage, redaction_type: redactionMode }
    setRedactionZones((prev) => {
      setUndoStack((s) => [...s, prev])
      setRedoStack([])
      return [...prev, newZone]
    })
  }, [currentPage, redactionMode])

  const handleRemoveZone = useCallback((index) => {
    setRedactionZones((prev) => {
      setUndoStack((s) => [...s, prev])
      setRedoStack([])
      return prev.filter((_, i) => i !== index)
    })
  }, [])

  const handleUndo = useCallback(() => {
    setUndoStack((prev) => {
      if (prev.length === 0) return prev
      const lastState = prev[prev.length - 1]
      setRedactionZones((current) => {
        setRedoStack((r) => [...r, current])
        return lastState
      })
      return prev.slice(0, -1)
    })
  }, [])

  const handleRedo = useCallback(() => {
    setRedoStack((prev) => {
      if (prev.length === 0) return prev
      const nextState = prev[prev.length - 1]
      setRedactionZones((current) => {
        setUndoStack((s) => [...s, current])
        return nextState
      })
      return prev.slice(0, -1)
    })
  }, [])

  const handleClearAll = useCallback(() => {
    setRedactionZones((prev) => {
      if (prev.length > 0) {
        setUndoStack((s) => [...s, prev])
        setRedoStack([])
      }
      return []
    })
    setSignatureZone(null)
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        handleUndo()
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z') || (e.shiftKey && e.key === 'Z'))) {
        e.preventDefault()
        handleRedo()
      }
      if (e.key === 'Delete' && redactionZones.length > 0) {
        handleClearAll()
      }
      if (e.key === 'Escape') {
        setSignatureZone(null)
        setTextZone(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleUndo, handleRedo, handleClearAll, redactionZones.length])

  const applyResultToViewer = useCallback(async (blob, filename) => {
    const newFile = new File([blob], filename, { type: 'application/pdf' })
    setPdfFile(newFile)
    setRedactionZones([])
    setUndoStack([])
    setRedoStack([])
    setCurrentPage(0)
    setResultBlobUrl(null)
    setSignatureZone(null)
    setTextZone(null)
    try {
      const info = await api.uploadPDF(newFile)
      setPdfInfo(info)
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Error recargando PDF: ${err.message}` })
    }
  }, [])

  const handleDownload = useCallback(() => {
    if (!pdfFile) return
    const url = resultBlobUrl || URL.createObjectURL(pdfFile)
    const a = document.createElement('a')
    a.href = url
    a.download = pdfFile.name
    a.click()
  }, [pdfFile, resultBlobUrl])

  const handleApplyRedaction = useCallback(async () => {
    if (!pdfFile || redactionZones.length === 0) {
      setStatusMessage({ type: 'error', text: 'Debe cargar un PDF y definir zonas de censura' })
      return
    }
    setLoading(true)
    setStatusMessage({ type: 'info', text: 'Aplicando censura irreversible...' })
    try {
      const { blob, verified } = await api.applyRedaction(pdfFile, redactionZones)
      await applyResultToViewer(blob, `REDACTED_${pdfFile.name}`)
      setStatusMessage({
        type: verified ? 'success' : 'warning',
        text: verified
          ? 'Censura aplicada y VERIFICADA exitosamente'
          : 'Censura aplicada. Advertencia: verificacion detecto posibles residuos',
      })
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Error: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }, [pdfFile, redactionZones, applyResultToViewer])

  const handleSanitizeMetadata = useCallback(async () => {
    if (!pdfFile) return
    setLoading(true)
    setStatusMessage({ type: 'info', text: 'Destruyendo metadatos...' })
    try {
      const blob = await api.sanitizeMetadata(pdfFile)
      await applyResultToViewer(blob instanceof Blob ? blob : await (await fetch(blob)).blob(), `SANITIZED_${pdfFile.name}`)
      setStatusMessage({ type: 'success', text: 'Metadatos destruidos exitosamente' })
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Error: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }, [pdfFile, applyResultToViewer])

  return (
    <div
      className={`app-container${isDragOver ? ' drag-over' : ''}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {isDragOver && (
        <div className="drag-overlay">
          <div className="drag-overlay-content">
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p>Suelte el archivo PDF aqui</p>
          </div>
        </div>
      )}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div>
            <h1 className="header-title">PDF Censura</h1>
            <p className="header-subtitle">Redaccion Irreversible &middot; Transparencia Activa Chile</p>
          </div>
        </div>
        <div className="header-actions">
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Cargar PDF
          </button>
          {pdfFile && (
            <button className="btn btn-secondary" onClick={handleDownload}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Descargar PDF
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </div>
      </header>

      {statusMessage && (
        <div className={`status-bar status-${statusMessage.type}`}>
          <div className="status-content">
            {loading && (
              <div className="status-progress-bar">
                <div className="status-progress-fill" />
              </div>
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="status-close">&times;</button>
        </div>
      )}

      <main className="app-main">
        <aside className="sidebar">
          <Toolbar
            redactionMode={redactionMode}
            setRedactionMode={setRedactionMode}
            redactionZones={redactionZones}
            onRemoveZone={handleRemoveZone}
            onApplyRedaction={handleApplyRedaction}
            loading={loading}
            setLoading={setLoading}
            pdfFile={pdfFile}
            activePanel={activePanel}
            setActivePanel={setActivePanel}
            onSanitizeMetadata={handleSanitizeMetadata}
            onApplyResult={applyResultToViewer}
            onUndo={handleUndo}
            onRedo={handleRedo}
            onClearAll={handleClearAll}
            canUndo={undoStack.length > 0}
            canRedo={redoStack.length > 0}
            textZone={textZone}
            onSetTextZone={setTextZone}
            textPreview={textPreview}
            onSetTextPreview={setTextPreview}
          />
        </aside>

        <section className="viewer-section">
          {pdfFile ? (
            <PDFViewer
              pdfFile={pdfFile}
              pdfInfo={pdfInfo}
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
              onAddZone={handleAddZone}
              redactionZones={redactionZones}
              redactionMode={
                activePanel === 'signature' ? 'signature'
                : activePanel === 'text' ? 'text'
                : redactionMode
              }
              onRemoveZone={handleRemoveZone}
              signatureZone={signatureZone}
              onAddSignature={setSignatureZone}
              textZone={textZone}
              onAddText={setTextZone}
              textPreview={textPreview}
            />
          ) : (
            <div className="empty-state">
              <div className="empty-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <h2>Cargue un documento PDF para comenzar</h2>
              <p>Seleccione un archivo para iniciar el proceso de redaccion segura</p>
              <button className="btn btn-primary btn-lg" onClick={() => fileInputRef.current?.click()}>
                Seleccionar PDF
              </button>
            </div>
          )}
        </section>

        {pdfFile && activePanel === 'metadata' && (
          <aside className="sidebar-right">
            <MetadataPanel pdfFile={pdfFile} onApplyResult={applyResultToViewer} setLoading={setLoading} />
          </aside>
        )}

        {pdfFile && activePanel === 'signature' && (
          <aside className="sidebar-right">
            <SignaturePanel pdfFile={pdfFile} onApplyResult={applyResultToViewer} signatureZone={signatureZone} />
          </aside>
        )}
      </main>
    </div>
  )
}
