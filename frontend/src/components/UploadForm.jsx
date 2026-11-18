import { UploadCloud } from 'lucide-react'
import { useRef, useState } from 'react'
import { errorMessage } from '../services/api'
import { ALLOWED_UPLOAD, DOCUMENT_TYPES, formatBytes, today } from '../utils/constants'
import { Alert, Field } from './ui'

/** Validates on the client, then calls `uploadFn(formData, onProgress)`. Backend re-validates everything. */
export default function UploadForm({ uploadFn, onUploaded }) {
  const [file, setFile] = useState(null)
  const [documentType, setDocumentType] = useState('PRESCRIPTION')
  const [documentDate, setDocumentDate] = useState('')
  const [documentName, setDocumentName] = useState('')
  const [progress, setProgress] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const inputRef = useRef(null)

  const validate = (f) => {
    if (!f) return 'Please choose a file.'
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
    if (!ALLOWED_UPLOAD.extensions.includes(ext) || (f.type && !ALLOWED_UPLOAD.mimes.includes(f.type))) {
      return 'Only PDF, JPG, JPEG or PNG files are allowed.'
    }
    if (f.size > ALLOWED_UPLOAD.maxBytes) return 'File is larger than 10 MB.'
    if (f.size === 0) return 'The selected file is empty.'
    return ''
  }

  const pick = (f) => {
    setSuccess('')
    const problem = validate(f)
    setError(problem)
    setFile(problem ? null : f)
  }

  const submit = async (e) => {
    e.preventDefault()
    const problem = validate(file)
    if (problem) return setError(problem)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('document_type', documentType)
    if (documentDate) fd.append('document_date', documentDate)
    if (documentName.trim()) fd.append('document_name', documentName.trim())
    setBusy(true); setError(''); setSuccess(''); setProgress(0)
    try {
      const { data } = await uploadFn(fd, (evt) => evt.total && setProgress(Math.round((evt.loaded / evt.total) * 100)))
      setSuccess(`"${data.document_name}" uploaded successfully.`)
      setFile(null); setDocumentName(''); setDocumentDate('')
      if (inputRef.current) inputRef.current.value = ''
      onUploaded?.(data)
    } catch (err) {
      setError(errorMessage(err, 'Upload failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-4">
      <h2 className="text-lg font-semibold">Upload a medical document</h2>
      <label
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files?.[0]) }}
        className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center transition hover:border-brand-500 hover:bg-brand-50"
      >
        <UploadCloud className="mb-2 h-10 w-10 text-brand-600" />
        {file ? (
          <span className="font-medium text-slate-800">{file.name} <span className="text-slate-500">({formatBytes(file.size)})</span></span>
        ) : (
          <>
            <span className="font-medium text-slate-800">Tap to choose a file or drag it here</span>
            <span className="mt-1 text-xs text-slate-500">PDF, JPG, JPEG or PNG · up to 10 MB</span>
          </>
        )}
        <input ref={inputRef} type="file" className="sr-only" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          onChange={(e) => pick(e.target.files?.[0])} />
      </label>

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Document category">
          <select className="input" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
            {DOCUMENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </Field>
        <Field label="Document date (optional)">
          <input type="date" className="input" max={today()} value={documentDate} onChange={(e) => setDocumentDate(e.target.value)} />
        </Field>
        <Field label="Title (optional)">
          <input className="input" maxLength={255} placeholder="e.g. Fever prescription" value={documentName}
            onChange={(e) => setDocumentName(e.target.value)} />
        </Field>
      </div>

      <Alert type="error">{error}</Alert>
      <Alert type="success">{success}</Alert>

      {busy && (
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
      <button type="submit" className="btn-primary w-full sm:w-auto" disabled={busy || !file}>
        <UploadCloud className="h-4 w-4" />{busy ? `Uploading… ${progress}%` : 'Upload document'}
      </button>
    </form>
  )
}
