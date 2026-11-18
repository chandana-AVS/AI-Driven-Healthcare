import { ArrowLeft, FileText } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DocumentCard from '../components/DocumentCard'
import HistoryTimeline from '../components/HistoryTimeline'
import RecordForm from '../components/RecordForm'
import UploadForm from '../components/UploadForm'
import { Alert, EmptyState, PageHeader, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { patientApi } from '../services/api'

export default function WorkerPatientView() {
  const { patientId } = useParams()
  const { user } = useAuth()
  const [tab, setTab] = useState('history')
  const history = useAsync(() => patientApi.historyOf(patientId), [patientId])
  const docs = useAsync(() => patientApi.documentsOf(patientId), [patientId])
  const refresh = () => { history.reload(); docs.reload() }

  if (history.error) {
    return (
      <div className="space-y-4">
        <Link to="/worker" className="btn-ghost"><ArrowLeft className="h-4 w-4" />Back</Link>
        <Alert type="error">{history.error}</Alert>
      </div>
    )
  }

  const tabs = [['history', 'Medical history'], ['documents', 'Documents'], ['add', 'Add record / upload']]

  return (
    <div className="space-y-6">
      <Link to="/worker" className="btn-ghost -ml-3"><ArrowLeft className="h-4 w-4" />All patients</Link>
      <PageHeader title={history.data?.patient_name || 'Patient'} subtitle="You are viewing records this patient has authorised you to access. Access is logged." />

      <div className="flex gap-1 rounded-2xl bg-slate-100 p-1">
        {tabs.map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex-1 rounded-xl px-4 py-2 text-sm font-semibold transition ${tab === key ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'history' && (history.loading ? <Spinner /> : <HistoryTimeline entries={history.data.entries} />)}

      {tab === 'documents' && (docs.loading ? <Spinner /> : docs.error ? <Alert type="error">{docs.error}</Alert> : docs.data.items.length === 0 ? (
        <EmptyState icon={FileText} title="No documents" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {docs.data.items.map((d) => (
            <DocumentCard key={d.id} doc={d} onDeleted={refresh} canDelete={d.uploaded_by === user.id} />
          ))}
        </div>
      ))}

      {tab === 'add' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <RecordForm documents={docs.data?.items || []} onSubmit={async (data) => { await patientApi.createRecord(patientId, data); refresh() }} />
          <UploadForm uploadFn={(fd, onProgress) => patientApi.uploadFor(patientId, fd, onProgress)} onUploaded={refresh} />
        </div>
      )}
    </div>
  )
}
