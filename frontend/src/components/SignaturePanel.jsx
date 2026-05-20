import { useState, useRef } from 'react'
import * as api from '../services/api'

export default function SignaturePanel({ pdfFile, onApplyResult, signatureZone, signaturePreview, onSignaturePreview }) {
  const [loading, setLoading] = useState(false)
  const [signatureType, setSignatureType] = useState('visual')

  const [certFile, setCertFile] = useState(null)
  const [certPassword, setCertPassword] = useState('')
  const certInputRef = useRef(null)

  const [ownerPwd, setOwnerPwd] = useState('')
  const [userPwd, setUserPwd] = useState('')
  const [allowPrint, setAllowPrint] = useState(false)
  const [allowCopy, setAllowCopy] = useState(false)

  const sp = signaturePreview
  const setSp = (update) => onSignaturePreview({ ...sp, ...update })

  const position = signatureZone
    ? { page: signatureZone.page, x: signatureZone.x, y: signatureZone.y, width: signatureZone.width, height: signatureZone.height }
    : { page: 0, x: 400, y: 700, width: 200, height: 80 }

  const handleVisualSign = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const blob = await api.addVisualSignature(
        pdfFile, position, sp.signerName, sp.signerRut, sp.reason, sp.includeHash, sp.includeBox
      )
      await onApplyResult(blob, `FIRMADO_${pdfFile.name}`)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDigitalSign = async () => {
    if (!pdfFile || !certFile) return
    setLoading(true)
    try {
      const blob = await api.digitalSignature(
        pdfFile, certFile, certPassword, position, sp.signerName, sp.reason
      )
      await onApplyResult(blob, `FIRMADO_DIGITAL_${pdfFile.name}`)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleProtect = async () => {
    if (!pdfFile) return
    setLoading(true)
    try {
      const blob = await api.protectPDF(pdfFile, {
        owner_password: ownerPwd,
        user_password: userPwd,
        allow_print: allowPrint,
        allow_copy: allowCopy,
        allow_modify: false,
        allow_annotate: false,
        encryption_level: 256,
      })
      await onApplyResult(blob, `PROTEGIDO_${pdfFile.name}`)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="side-panel">
      <h3 className="panel-title">Firma Electronica</h3>

      <div className="form-group">
        <label>Nombre del Firmante</label>
        <input type="text" value={sp.signerName} onChange={(e) => setSp({ signerName: e.target.value })} placeholder="Juan Perez Lopez" />
      </div>
      <div className="form-group">
        <label>RUT</label>
        <input type="text" value={sp.signerRut} onChange={(e) => setSp({ signerRut: e.target.value })} placeholder="12.345.678-9" />
      </div>
      <div className="form-group">
        <label>Motivo</label>
        <input type="text" value={sp.reason} onChange={(e) => setSp({ reason: e.target.value })} />
      </div>

      <div className="sig-position-info">
        {signatureZone ? (
          <p className="sig-position-set">
            Zona de firma definida en Pag. {signatureZone.page + 1}
          </p>
        ) : (
          <p className="sig-position-hint">
            Dibuje una zona en el visor para ubicar la firma
          </p>
        )}
      </div>

      <div className="form-group">
        <label>Tipo de Firma</label>
        <div className="sig-type-tabs">
          <button
            className={`sig-type-btn ${signatureType === 'visual' ? 'active' : ''}`}
            onClick={() => setSignatureType('visual')}
          >
            Visual
          </button>
          <button
            className={`sig-type-btn ${signatureType === 'digital' ? 'active' : ''}`}
            onClick={() => setSignatureType('digital')}
          >
            Digital PKCS#7
          </button>
        </div>
      </div>

      {signatureType === 'visual' && (
        <>
          <div className="form-group">
            <label className="checkbox-label">
              <input type="checkbox" checked={sp.includeHash} onChange={(e) => setSp({ includeHash: e.target.checked })} />
              Incluir hash SHA-256 de integridad
            </label>
          </div>
          <div className="form-group">
            <label className="checkbox-label">
              <input type="checkbox" checked={sp.includeBox} onChange={(e) => setSp({ includeBox: e.target.checked })} />
              Incluir recuadro azul
            </label>
          </div>
          <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleVisualSign}>
            {loading ? 'Firmando...' : 'Aplicar Firma Visual'}
          </button>
        </>
      )}

      {signatureType === 'digital' && (
        <>
          <div className="form-group">
            <label>Certificado (.p12 / .pfx)</label>
            <button
              className="btn btn-sm btn-full cert-upload-btn"
              onClick={() => certInputRef.current?.click()}
            >
              {certFile ? certFile.name : 'Seleccionar certificado'}
            </button>
            <input
              ref={certInputRef}
              type="file"
              accept=".p12,.pfx"
              onChange={(e) => setCertFile(e.target.files?.[0] || null)}
              style={{ display: 'none' }}
            />
          </div>
          <div className="form-group">
            <label>Contrasena del Certificado</label>
            <input
              type="password"
              value={certPassword}
              onChange={(e) => setCertPassword(e.target.value)}
              placeholder="Password del .p12"
            />
          </div>
          <button
            className="btn btn-primary btn-full"
            disabled={!pdfFile || !certFile || loading}
            onClick={handleDigitalSign}
          >
            {loading ? 'Firmando digitalmente...' : 'Firmar con Certificado Digital'}
          </button>
          <p className="cert-hint">
            Requiere un certificado .p12/.pfx emitido por una Autoridad Certificadora valida.
          </p>
        </>
      )}

      <hr className="divider" />

      <h3 className="panel-title">Proteccion</h3>
      <div className="form-group">
        <label>Contrasena Propietario</label>
        <input type="password" value={ownerPwd} onChange={(e) => setOwnerPwd(e.target.value)} />
      </div>
      <div className="form-group">
        <label>Contrasena Usuario</label>
        <input type="password" value={userPwd} onChange={(e) => setUserPwd(e.target.value)} />
      </div>
      <div className="form-group">
        <label className="checkbox-label">
          <input type="checkbox" checked={allowPrint} onChange={(e) => setAllowPrint(e.target.checked)} />
          Permitir impresion
        </label>
      </div>
      <div className="form-group">
        <label className="checkbox-label">
          <input type="checkbox" checked={allowCopy} onChange={(e) => setAllowCopy(e.target.checked)} />
          Permitir copia de texto
        </label>
      </div>
      <button className="btn btn-primary btn-full" disabled={!pdfFile || loading} onClick={handleProtect}>
        {loading ? 'Protegiendo...' : 'Encriptar PDF (AES-256)'}
      </button>
    </div>
  )
}
