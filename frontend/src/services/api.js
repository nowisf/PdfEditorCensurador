import axios from 'axios'

const API_BASE = window.location.hostname === 'localhost' ? '/api' : '/_/backend/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
})

export async function uploadPDF(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/upload', formData)
  return data
}

export async function renderPage(file, page = 0, dpi = 150) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('page', page)
  formData.append('dpi', dpi)
  const { data } = await api.post('/redaction/render-page', formData, {
    responseType: 'blob',
  })
  return URL.createObjectURL(data)
}

export async function getPageInfo(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/redaction/page-info', formData)
  return data
}

export async function applyRedaction(file, zones, imageMethod = 'blackout', pixelateBlock = 15) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('zones_json', JSON.stringify(zones))
  formData.append('image_method', imageMethod)
  formData.append('pixelate_block_size', pixelateBlock)
  const response = await api.post('/redaction/apply-redaction', formData, {
    responseType: 'blob',
  })
  const verified = response.headers['x-redaction-verified']
  return { blob: response.data, verified: verified === 'True' }
}

export async function inspectMetadata(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/metadata/inspect', formData)
  return data
}

export async function sanitizeMetadata(file, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('options_json', JSON.stringify(options))
  const response = await api.post('/metadata/sanitize', formData, {
    responseType: 'blob',
  })
  return response.data
}

export async function addVisualSignature(file, position, signerName, signerRut, reason, includeHash = true, includeBox = true) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('position_json', JSON.stringify(position))
  formData.append('signer_name', signerName)
  formData.append('signer_rut', signerRut)
  formData.append('reason', reason)
  formData.append('include_hash', String(includeHash))
  formData.append('include_box', String(includeBox))
  const response = await api.post('/signature/visual-signature', formData, {
    responseType: 'blob',
  })
  return response.data
}

export async function digitalSignature(file, certificate, certPassword, position, signerName, reason) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('certificate', certificate)
  formData.append('cert_password', certPassword)
  formData.append('position_json', JSON.stringify(position))
  formData.append('signer_name', signerName)
  formData.append('reason', reason)
  const response = await api.post('/signature/digital-signature', formData, {
    responseType: 'blob',
  })
  return response.data
}

export async function protectPDF(file, options) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('options_json', JSON.stringify(options))
  const response = await api.post('/signature/protect', formData, {
    responseType: 'blob',
  })
  return response.data
}

export async function extractText(file, page = 0) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('page', page)
  const { data } = await api.post('/redaction/extract-text', formData)
  return data
}

export async function detectSensitive(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/tools/detect-sensitive', formData)
  return data
}

export async function rotatePages(file, pages = [], degrees = 90) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('pages_json', JSON.stringify(pages))
  formData.append('degrees', degrees)
  const response = await api.post('/tools/rotate-pages', formData, { responseType: 'blob' })
  return response.data
}

export async function deletePages(file, pages) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('pages_json', JSON.stringify(pages))
  const response = await api.post('/tools/delete-pages', formData, { responseType: 'blob' })
  return response.data
}

export async function reorderPages(file, order) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('order_json', JSON.stringify(order))
  const response = await api.post('/tools/reorder-pages', formData, { responseType: 'blob' })
  return response.data
}

export async function applyWatermark(file, text = 'CONFIDENCIAL', opacity = 0.15, fontsize = 60, angle = 45) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('text', text)
  formData.append('opacity', opacity)
  formData.append('fontsize', fontsize)
  formData.append('angle', angle)
  const response = await api.post('/tools/watermark', formData, { responseType: 'blob' })
  return response.data
}

export async function applyStamp(file, text = 'CENSURADO', page = 0, x = 400, y = 50) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('text', text)
  formData.append('page', page)
  formData.append('x', x)
  formData.append('y', y)
  const response = await api.post('/tools/stamp', formData, { responseType: 'blob' })
  return response.data
}

export async function getAuditLogs(date = null, limit = 100) {
  const params = new URLSearchParams()
  if (date) params.append('date', date)
  params.append('limit', limit)
  const { data } = await api.get(`/tools/audit-logs?${params.toString()}`)
  return data
}

export async function getAuditStats() {
  const { data } = await api.get('/tools/audit-stats')
  return data
}

export async function addPages(file, count = 1, position = 'end', width = 612, height = 792, content = '') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('count', count)
  formData.append('position', position)
  formData.append('width', width)
  formData.append('height', height)
  formData.append('content', content)
  const response = await api.post('/tools/add-pages', formData, { responseType: 'blob' })
  return response.data
}

export async function addText(file, page, x, y, width, height, text, fontsize = 12, align = 0, customFont = null, fontname = 'helv') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('page', page)
  formData.append('x', x)
  formData.append('y', y)
  formData.append('width', width)
  formData.append('height', height)
  formData.append('text', text)
  formData.append('fontsize', fontsize)
  formData.append('align', align)
  formData.append('fontname', fontname)
  if (customFont) {
    formData.append('fontfile', customFont)
  }
  const response = await api.post('/tools/add-text', formData, { responseType: 'blob' })
  return response.data
}
