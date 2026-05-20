import { useState, useEffect } from 'react'
import * as api from '../services/api'

const FIELD_LABELS = {
  author: 'Autor',
  creator: 'Creador',
  producer: 'Productor',
  title: 'Titulo',
  subject: 'Asunto',
  keywords: 'Palabras clave',
  creationDate: 'Fecha creacion',
  modDate: 'Fecha modificacion',
}

const FIELD_OPTION_MAP = {
  author: 'remove_author',
  creator: 'remove_creator',
  producer: 'remove_producer',
  title: 'remove_title',
  subject: 'remove_subject',
  keywords: 'remove_keywords',
  creationDate: 'remove_creation_date',
  modDate: 'remove_mod_date',
}

const RISK_LABELS = {
  has_xmp: { label: 'Metadatos XMP', risk_key: 'has_xmp', option: 'remove_all_xml_metadata' },
  has_thumbnails: { label: 'Miniaturas', risk_key: 'has_thumbnails', option: 'remove_thumbnails' },
  has_piece_info: { label: 'Piece Info', risk_key: 'has_piece_info', option: null },
}

export default function MetadataPanel({ pdfFile, onApplyResult, setLoading }) {
  const [metadata, setMetadata] = useState(null)
  const [loadingMeta, setLoadingMeta] = useState(false)

  const loadMetadata = () => {
    if (!pdfFile) return
    setLoadingMeta(true)
    api.inspectMetadata(pdfFile)
      .then(setMetadata)
      .catch(() => setMetadata(null))
      .finally(() => setLoadingMeta(false))
  }

  useEffect(() => { loadMetadata() }, [pdfFile])

  const handleRemoveField = async (fieldKey) => {
    const optionKey = FIELD_OPTION_MAP[fieldKey]
    if (!optionKey) return
    const options = { [optionKey]: true }
    if (setLoading) setLoading(true)
    try {
      const blob = await api.sanitizeMetadata(pdfFile, options)
      if (onApplyResult) {
        await onApplyResult(blob, `SANITIZED_${pdfFile.name}`)
      }
      setTimeout(loadMetadata, 300)
    } catch (err) {
      alert('Error eliminando metadato: ' + err.message)
    } finally {
      if (setLoading) setLoading(false)
    }
  }

  const handleRemoveRisk = async (riskId) => {
    const risk = RISK_LABELS[riskId]
    if (!risk || !risk.option) return
    const options = { [risk.option]: true }
    if (setLoading) setLoading(true)
    try {
      const blob = await api.sanitizeMetadata(pdfFile, options)
      if (onApplyResult) {
        await onApplyResult(blob, `SANITIZED_${pdfFile.name}`)
      }
      setTimeout(loadMetadata, 300)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      if (setLoading) setLoading(false)
    }
  }

  if (loadingMeta) return <div className="side-panel"><p>Cargando metadatos...</p></div>
  if (!metadata) return <div className="side-panel"><p>No se pudieron cargar los metadatos</p></div>

  return (
    <div className="side-panel">
      <h3 className="panel-title">Inspeccion de Metadatos</h3>

      <div className="meta-section">
        <h4>Campos Estandar</h4>
        {Object.entries(metadata.standard_fields || {}).map(([key, value]) => (
          <div key={key} className="meta-row">
            <div className="meta-row-content">
              <span className="meta-key">{FIELD_LABELS[key] || key}</span>
              <span className="meta-value">{value || <em>(vacio)</em>}</span>
            </div>
            <button
              className="meta-delete-btn"
              title={`Eliminar ${FIELD_LABELS[key] || key}`}
              onClick={() => handleRemoveField(key)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                <line x1="10" y1="11" x2="10" y2="17" />
                <line x1="14" y1="11" x2="14" y2="17" />
              </svg>
            </button>
          </div>
        ))}
        {Object.keys(metadata.standard_fields || {}).length === 0 && (
          <p className="meta-empty">No se encontraron metadatos</p>
        )}
      </div>

      <div className="meta-section">
        <h4>Analisis de Riesgo</h4>
        <div className="meta-row">
          <div className="meta-row-content">
            <span className="meta-key">Paginas</span>
            <span className="meta-value">{metadata.page_count}</span>
          </div>
        </div>
        {Object.entries(RISK_LABELS).map(([riskId, risk]) => {
          const isPresent = metadata[risk.risk_key]
          return (
            <div key={riskId} className={`meta-row ${isPresent ? 'risk-high' : 'risk-none'}`}>
              <div className="meta-row-content">
                <span className="meta-key">{risk.label}</span>
                <span className="meta-value">{isPresent ? 'PRESENTE - Riesgo' : 'No detectado'}</span>
              </div>
              {isPresent && risk.option && (
                <button
                  className="meta-delete-btn"
                  title={`Eliminar ${risk.label}`}
                  onClick={() => handleRemoveRisk(riskId)}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
