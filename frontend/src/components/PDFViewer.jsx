import { useState, useRef, useEffect, useCallback } from 'react'
import * as api from '../services/api'

export default function PDFViewer({
  pdfFile,
  pdfInfo,
  currentPage,
  setCurrentPage,
  onAddZone,
  redactionZones,
  redactionMode,
  onRemoveZone,
  signatureZone,
  onAddSignature,
  textZone,
  onAddText,
  textPreview,
  signaturePreview,
}) {
  const [pageImages, setPageImages] = useState({})
  const [scale, setScale] = useState(1)
  const [drawing, setDrawing] = useState(false)
  const [drawStart, setDrawStart] = useState(null)
  const [drawCurrent, setDrawCurrent] = useState(null)
  const [activePage, setActivePage] = useState(0)
  const pageRefs = useRef({})
  const scrollRef = useRef(null)

  const totalPages = pdfInfo?.pages || 0

  useEffect(() => {
    if (!pdfFile || totalPages === 0) return
    let cancelled = false
    const images = {}
    const loadPages = async () => {
      for (let i = 0; i < totalPages; i++) {
        if (cancelled) return
        try {
          const url = await api.renderPage(pdfFile, i, 150)
          if (cancelled) return
          images[i] = url
          setPageImages({ ...images })
        } catch (err) {
          console.error(`Error rendering page ${i}:`, err)
        }
      }
    }
    loadPages()
    return () => { cancelled = true }
  }, [pdfFile, totalPages])

  const isInteractive = redactionMode !== 'select'

  useEffect(() => {
    const scrollEl = scrollRef.current
    if (!scrollEl || totalPages === 0) return

    const handleScroll = () => {
      const scrollTop = scrollEl.scrollTop
      let acc = 0
      for (let i = 0; i < totalPages; i++) {
        const el = pageRefs.current[i]
        if (!el) continue
        const pageH = el.offsetHeight + 16
        if (scrollTop < acc + pageH * 0.5) {
          if (i !== activePage) {
            setActivePage(i)
            setCurrentPage(i)
          }
          return
        }
        acc += pageH
      }
    }

    scrollEl.addEventListener('scroll', handleScroll, { passive: true })
    return () => scrollEl.removeEventListener('scroll', handleScroll)
  }, [totalPages, activePage, setCurrentPage])

  const scrollToPage = useCallback((pageIdx) => {
    const el = pageRefs.current[pageIdx]
    if (el && scrollRef.current) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])

  useEffect(() => {
    if (currentPage !== activePage) {
      scrollToPage(currentPage)
    }
  }, [currentPage])

  const getPageInfo = useCallback((pageIdx) => {
    return pdfInfo?.page_details?.[pageIdx]
  }, [pdfInfo])

  const handleMouseDown = useCallback((e) => {
    if (redactionMode === 'select') return
    const rect = e.currentTarget.getBoundingClientRect()
    setDrawStart({ x: e.clientX - rect.left, y: e.clientY - rect.top, page: parseInt(e.currentTarget.dataset.page) })
    setDrawCurrent({ x: e.clientX - rect.left, y: e.clientY - rect.top })
    setDrawing(true)
  }, [redactionMode])

  const handleMouseMove = useCallback((e) => {
    if (!drawing) return
    const rect = e.currentTarget.getBoundingClientRect()
    setDrawCurrent({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [drawing])

  const handleMouseUp = useCallback((e) => {
    if (!drawing || !drawStart) return
    const rect = e.currentTarget.getBoundingClientRect()
    const endX = e.clientX - rect.left
    const endY = e.clientY - rect.top

    const x = Math.min(drawStart.x, endX)
    const y = Math.min(drawStart.y, endY)
    const width = Math.abs(endX - drawStart.x)
    const height = Math.abs(endY - drawStart.y)
    const pageIdx = drawStart.page

    if (width > 5 && height > 5) {
      const pi = getPageInfo(pageIdx)
      const el = pageRefs.current[pageIdx]
      if (pi && el) {
        const elRect = el.getBoundingClientRect()
        const sx = pi.width / elRect.width
        const sy = pi.height / elRect.height
        const pdfCoords = {
          x: x * sx,
          y: y * sy,
          width: width * sx,
          height: height * sy,
        }
        if (redactionMode === 'signature') {
          onAddSignature({ page: pageIdx, ...pdfCoords })
        } else if (redactionMode === 'text-insert') {
          onAddText({ page: pageIdx, ...pdfCoords })
        } else {
          onAddZone({ ...pdfCoords, page: pageIdx })
        }
      }
    }

    setDrawing(false)
    setDrawStart(null)
    setDrawCurrent(null)
  }, [drawing, drawStart, redactionMode, getPageInfo, onAddZone, onAddSignature, onAddText])

  const indicatorText = redactionMode === 'signature'
    ? 'Modo firma activo - Dibuje la zona para la firma'
    : redactionMode === 'text-insert'
    ? 'Modo texto activo - Dibuje la zona donde insertar texto'
    : 'Modo censura activo - Dibuje zonas sobre el documento'

  const renderPageZones = (pageIdx) => {
    const pi = getPageInfo(pageIdx)
    const el = pageRefs.current[pageIdx]
    if (!pi || !el) return null
    const elRect = el.getBoundingClientRect()
    const sx = elRect.width / pi.width
    const sy = elRect.height / pi.height

    const zones = redactionZones.filter((z) => z.page === pageIdx)
    const elements = []

    zones.forEach((zone) => {
      const idx = redactionZones.indexOf(zone)
      elements.push(
        <div key={`zone-${idx}`} className={`redaction-zone zone-${zone.redaction_type}`}
          style={{ left: zone.x * sx, top: zone.y * sy, width: zone.width * sx, height: zone.height * sy }}>
          <div className="zone-label">
            {zone.redaction_type === 'text' ? 'TEXTO' : zone.redaction_type === 'image' ? 'IMAGEN' : 'REGION'}
          </div>
          <button className="zone-remove" onClick={(e) => { e.stopPropagation(); onRemoveZone(idx) }}>&times;</button>
        </div>
      )
    })

    if (signatureZone && signatureZone.page === pageIdx) {
      const sigLines = []
      if (signaturePreview?.signerName) sigLines.push(`Firmado por: ${signaturePreview.signerName}`)
      if (signaturePreview?.signerRut) sigLines.push(`RUT: ${signaturePreview.signerRut}`)
      sigLines.push(`Motivo: ${signaturePreview?.reason || 'Firma'}`)
      if (signaturePreview?.includeHash) {
        sigLines.push('SHA-256: (hash al firmar)')
      }
      const sigFontSize = 7 * (elRect.width / pi.width)
      elements.push(
        <div key="sig" className="redaction-zone zone-signature"
          style={{ left: signatureZone.x * sx, top: signatureZone.y * sy, width: signatureZone.width * sx, height: signatureZone.height * sy }}>
          <div className="zone-label">FIRMA</div>
          {signaturePreview && sigLines.length > 0 && (
            <div className="sig-preview-content" style={{
              fontSize: sigFontSize,
              lineHeight: 1.4,
              padding: `${sigFontSize * 0.5}px ${sigFontSize}px`,
              color: '#111',
              fontFamily: 'Helvetica, Arial, sans-serif',
            }}>
              {sigLines.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          )}
        </div>
      )
    }

    if (textZone && textZone.page === pageIdx) {
      const previewFontSize = textPreview?.fontSize ? textPreview.fontSize * (elRect.width / pi.width) : 12 * (elRect.width / pi.width)
      const previewAlign = textPreview?.align === 1 ? 'center' : textPreview?.align === 2 ? 'right' : 'left'
      const BUILTIN_FONTS_CSS = {
        helv: 'Helvetica, Arial, sans-serif',
        cour: '"Courier New", Courier, monospace',
        tiro: '"Times New Roman", Times, serif',
        symb: 'Symbol',
        zadb: '"Zapf Dingbats"',
      }
      const previewFont = textPreview?.font && textPreview.font !== 'custom'
        ? (BUILTIN_FONTS_CSS[textPreview.font] || 'Helvetica, Arial, sans-serif')
        : 'Helvetica, Arial, sans-serif'

      elements.push(
        <div key="txt" className="redaction-zone zone-text-insert"
          style={{ left: textZone.x * sx, top: textZone.y * sy, width: textZone.width * sx, height: textZone.height * sy }}>
          <div className="zone-label">TEXTO</div>
          {textPreview?.content && (
            <div className="text-preview-content" style={{
              fontSize: previewFontSize,
              fontFamily: previewFont,
              textAlign: previewAlign,
              lineHeight: 1.2,
              padding: '4px',
              overflow: 'hidden',
              wordBreak: 'break-word',
            }}>
              {textPreview.content}
            </div>
          )}
        </div>
      )
    }

    if (drawing && drawStart && drawStart.page === pageIdx && drawCurrent) {
      elements.push(
        <div key="draw" className={`redaction-zone ${
          redactionMode === 'signature' ? 'zone-drawing-signature'
          : redactionMode === 'text-insert' ? 'zone-drawing-text'
          : 'zone-drawing'
        }`} style={{
          left: Math.min(drawStart.x, drawCurrent.x),
          top: Math.min(drawStart.y, drawCurrent.y),
          width: Math.abs(drawCurrent.x - drawStart.x),
          height: Math.abs(drawCurrent.y - drawStart.y),
        }} />
      )
    }

    return elements
  }

  return (
    <div className="pdf-viewer">
      <div className="viewer-toolbar">
        <div className="page-nav">
          <button className="btn btn-sm" disabled={currentPage === 0} onClick={() => scrollToPage(currentPage - 1)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <span className="page-indicator">{activePage + 1} / {totalPages || '?'}</span>
          <button className="btn btn-sm" disabled={currentPage >= totalPages - 1} onClick={() => scrollToPage(currentPage + 1)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>
        <div className="zoom-controls">
          <button className="btn btn-sm" onClick={() => setScale((s) => Math.max(0.3, s - 0.1))}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12" /></svg>
          </button>
          <span className="zoom-label">{Math.round(scale * 100)}%</span>
          <button className="btn btn-sm" onClick={() => setScale((s) => Math.min(3, s + 0.1))}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          </button>
        </div>
        {isInteractive && (
          <div className={`drawing-indicator ${redactionMode === 'signature' ? 'indicator-signature' : redactionMode === 'text-insert' ? 'indicator-text' : ''}`}>
            <span className={`pulse-dot ${redactionMode === 'signature' ? 'dot-signature' : redactionMode === 'text-insert' ? 'dot-text' : ''}`} />
            {indicatorText}
          </div>
        )}
      </div>

      <div className="viewer-scroll-area" ref={scrollRef}>
        <div className="pages-container">
          {Array.from({ length: totalPages }, (_, pageIdx) => {
            const pi = getPageInfo(pageIdx)
            return (
              <div
                key={pageIdx}
                data-page={pageIdx}
                ref={(el) => { pageRefs.current[pageIdx] = el }}
                className="page-wrapper"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                style={{
                  cursor: isInteractive ? 'crosshair' : 'default',
                  width: pi ? pi.width * scale : undefined,
                  height: pi ? pi.height * scale : undefined,
                }}
              >
                {pageImages[pageIdx] ? (
                  <img
                    src={pageImages[pageIdx]}
                    alt={`Pagina ${pageIdx + 1}`}
                    className="page-image"
                    draggable={false}
                    style={{ width: '100%', height: '100%' }}
                  />
                ) : (
                  <div className="page-placeholder" style={{ width: '100%', height: '100%' }}>
                    <span>Cargando...</span>
                  </div>
                )}

                {renderPageZones(pageIdx)}
                <div className="page-number-badge">{pageIdx + 1}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
