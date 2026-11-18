import { FileText } from 'lucide-react'
import { useState } from 'react'
import DocumentCard from '../components/DocumentCard'
import UploadForm from '../components/UploadForm'
import { Alert, EmptyState, PageHeader, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { patientApi } from '../services/api'
import { DOCUMENT_TYPES } from '../utils/constants'

export default function Documents() {
  const [filter, setFilter] = useState('')
  const docs = useAsync(() => patientApi.documents(filter ? { document_type: filter } : undefined), [filter])

  return (
    <div className="space-y-8">
      <PageHeader title="My Documents" subtitle="Prescriptions, discharge summaries, diagnostic and lab reports — stored privately." />
      <UploadForm uploadFn={patientApi.upload} onUploaded={docs.reload} />

      <section>
        <div className="mb-4 flex flex-wrap gap-2">
          {[{ value: '', label: 'All' }, ...DOCUMENT_TYPES].map((t) => (
            <button key={t.value} onClick={() => setFilter(t.value)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${filter === t.value ? 'bg-brand-700 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'}`}>
              {t.label}
            </button>
          ))}
        </div>
        {docs.loading ? <Spinner /> : docs.error ? <Alert type="error">{docs.error}</Alert> : docs.data.items.length === 0 ? (
          <EmptyState icon={FileText} title="No documents found">{filter ? 'Try another category.' : 'Upload a document to get started.'}</EmptyState>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {docs.data.items.map((d) => <DocumentCard key={d.id} doc={d} onDeleted={docs.reload} />)}
          </div>
        )}
      </section>
    </div>
  )
}
