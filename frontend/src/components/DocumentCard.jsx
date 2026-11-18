import { Download, Eye, FileImage, FileText, Languages, Sparkles, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { documentApi, errorMessage } from '../services/api'
import { formatBytes, formatDate, labelFor, languageLabel } from '../utils/constants'
import { StatusBadge } from './ui'

const TYPE_COLORS = {
  PRESCRIPTION: 'bg-sky-50 text-sky-700',
  DISCHARGE_SUMMARY: 'bg-violet-50 text-violet-700',
  DIAGNOSTIC_REPORT: 'bg-amber-50 text-amber-700',
  LAB_REPORT: 'bg-emerald-50 text-emerald-700',
  OTHER: 'bg-slate-100 text-slate-700',
}

export default function DocumentCard({ doc, onDeleted, canDelete = true }) {
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const Icon = doc.mime_type === 'application/pdf' ? FileText : FileImage

  const run = async (kind, fn) => {
    setBusy(kind)
    setError('')
    try { await fn() } catch (err) { setError(errorMessage(err)) } finally { setBusy('') }
  }

  const handleDelete = () => {
    if (!window.confirm(`Delete "${doc.document_name}"? This cannot be undone.`)) return
    run('delete', async () => { await documentApi.remove(doc.id); onDeleted?.(doc.id) })
  }

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className={`rounded-xl p-2.5 ${TYPE_COLORS[doc.document_type] || TYPE_COLORS.OTHER}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate font-semibold text-slate-900" title={doc.document_name}>{doc.document_name}</div>
          <div className="text-sm text-slate-500">{labelFor(doc.document_type)}</div>
        </div>
        <StatusBadge status={doc.processing_status} />
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-500">
        <dt>Uploaded</dt><dd className="text-right text-slate-700">{formatDate(doc.created_at)}</dd>
        {doc.document_date && (<><dt>Document date</dt><dd className="text-right text-slate-700">{formatDate(doc.document_date)}</dd></>)}
        <dt>Size</dt><dd className="text-right text-slate-700">{formatBytes(doc.file_size)}</dd>
      </dl>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {doc.translated_languages?.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="flex items-center gap-1 font-medium text-slate-500"><Languages className="h-3.5 w-3.5" />Translated:</span>
          {doc.translated_languages.map((code) => (
            <Link key={code} to={`/documents/${doc.id}/explain?lang=${code}`}
              className="rounded-full bg-brand-50 px-2.5 py-1 font-medium text-brand-800 hover:bg-brand-100">
              {languageLabel(code)}
            </Link>
          ))}
        </div>
      )}
      <Link to={`/documents/${doc.id}/explain`} className="btn-primary mt-auto px-3 py-2">
        <Sparkles className="h-4 w-4" />{doc.translated_languages?.length ? 'Open translation' : 'Explain & translate'}
      </Link>
      <div className="flex gap-2">
        <button className="btn-secondary flex-1 px-3 py-2" disabled={!!busy} onClick={() => run('view', () => documentApi.view(doc))}>
          <Eye className="h-4 w-4" />View
        </button>
        <button className="btn-secondary flex-1 px-3 py-2" disabled={!!busy} onClick={() => run('download', () => documentApi.download(doc))}>
          <Download className="h-4 w-4" />{busy === 'download' ? '…' : 'Download'}
        </button>
        {canDelete && (
          <button className="btn-ghost px-3 py-2 text-red-600 hover:bg-red-50" disabled={!!busy} onClick={handleDelete} aria-label="Delete document">
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
