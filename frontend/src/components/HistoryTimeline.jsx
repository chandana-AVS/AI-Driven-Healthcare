import { ClipboardList, Download, FileText, History } from 'lucide-react'
import { documentApi } from '../services/api'
import { formatDate, labelFor } from '../utils/constants'
import { EmptyState, StatusBadge } from './ui'

/** Chronological patient history (records + documents), newest first. */
export default function HistoryTimeline({ entries }) {
  if (!entries?.length) {
    return <EmptyState icon={History} title="No medical history yet">Uploaded documents and healthcare records will appear here.</EmptyState>
  }
  return (
    <ol className="relative space-y-4 border-l-2 border-slate-200 pl-6">
      {entries.map((e) => {
        const isDoc = e.entry_type === 'DOCUMENT'
        const Icon = isDoc ? FileText : ClipboardList
        const key = isDoc ? `d-${e.document.id}` : `r-${e.record.id}`
        return (
          <li key={key} className="relative">
            <span className={`absolute -left-[37px] top-4 flex h-7 w-7 items-center justify-center rounded-full ring-4 ring-slate-50 ${isDoc ? 'bg-sky-100 text-sky-700' : 'bg-brand-100 text-brand-700'}`}>
              <Icon className="h-3.5 w-3.5" />
            </span>
            <div className="card">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{labelFor(e.category)}</div>
                  <div className="text-base font-semibold text-slate-900">{e.title}</div>
                </div>
                <div className="text-right text-sm text-slate-500">{formatDate(e.date)}</div>
              </div>
              {e.description && <p className="mt-2 whitespace-pre-line text-sm text-slate-700">{e.description}</p>}
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                {isDoc ? (
                  <>
                    <span>Uploaded: {formatDate(e.timestamp)}</span>
                    <span className="flex items-center gap-1">Status: <StatusBadge status={e.status} /></span>
                    <button className="ml-auto inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline" onClick={() => documentApi.download(e.document)}>
                      <Download className="h-3.5 w-3.5" />Download
                    </button>
                  </>
                ) : (
                  <>
                    {e.record.created_by_name && <span>Added by {e.record.created_by_name}</span>}
                    {e.record.document_id && <span className="badge bg-sky-50 text-sky-700">Linked document</span>}
                  </>
                )}
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
