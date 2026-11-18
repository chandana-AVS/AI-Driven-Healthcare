export const LANGUAGES = [
  { code: 'en', name: 'English', native: 'English' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'Malayalam', native: 'മലയാളം' },
]

export const languageLabel = (code) => {
  const l = LANGUAGES.find((x) => x.code === code)
  return l ? `${l.name} (${l.native})` : code
}

export const DOCUMENT_TYPES = [
  { value: 'PRESCRIPTION', label: 'Prescription' },
  { value: 'DISCHARGE_SUMMARY', label: 'Discharge Summary' },
  { value: 'DIAGNOSTIC_REPORT', label: 'Diagnostic Report' },
  { value: 'LAB_REPORT', label: 'Lab Report' },
  { value: 'OTHER', label: 'Other' },
]

export const RECORD_TYPES = [
  { value: 'CONSULTATION', label: 'Consultation' },
  { value: 'DIAGNOSIS', label: 'Diagnosis' },
  { value: 'PRESCRIPTION', label: 'Prescription' },
  { value: 'DISCHARGE', label: 'Discharge' },
  { value: 'LAB_RESULT', label: 'Lab Result' },
  { value: 'IMMUNIZATION', label: 'Immunization' },
  { value: 'NOTE', label: 'Note' },
  { value: 'OTHER', label: 'Other' },
]

export const CONTENT_CATEGORIES = [
  { value: 'GENERAL_HEALTH', label: 'General Health' },
  { value: 'MATERNAL_HEALTH', label: 'Maternal Health' },
  { value: 'CHILD_HEALTHCARE', label: 'Child Healthcare' },
  { value: 'ELDERLY_CARE', label: 'Elderly Care' },
  { value: 'PREVENTIVE_HEALTHCARE', label: 'Preventive Healthcare' },
  { value: 'COMMON_DISEASES', label: 'Common Diseases' },
]

export const CONTENT_TYPES = [
  { value: 'ARTICLE', label: 'Article' },
  { value: 'FAQ', label: 'FAQ' },
  { value: 'DISEASE_INFO', label: 'Disease information' },
]

export const TEXT_TYPES = [
  { value: 'PRESCRIPTION', label: 'Prescription' },
  { value: 'DISCHARGE_SUMMARY', label: 'Discharge summary' },
  { value: 'INSTRUCTIONS', label: 'Healthcare instructions' },
  { value: 'GENERAL', label: 'Other medical text' },
]

const ALL_LABELS = Object.fromEntries(
  [...DOCUMENT_TYPES, ...RECORD_TYPES, ...CONTENT_CATEGORIES, ...CONTENT_TYPES].map((x) => [x.value, x.label]),
)
export const labelFor = (value) => ALL_LABELS[value] || value?.replaceAll('_', ' ').toLowerCase()

export const ALLOWED_UPLOAD = {
  extensions: ['.pdf', '.jpg', '.jpeg', '.png'],
  mimes: ['application/pdf', 'image/jpeg', 'image/png'],
  maxBytes: 10 * 1024 * 1024,
}

export const ROLE_HOME = {
  PATIENT: '/patient',
  HEALTHCARE_WORKER: '/worker',
  ADMIN: '/admin',
}

export const formatDate = (value) =>
  value ? new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
  }) : '—'

export const formatDateTime = (value) =>
  value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

export const formatBytes = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`
}

export const today = () => new Date().toISOString().slice(0, 10)
