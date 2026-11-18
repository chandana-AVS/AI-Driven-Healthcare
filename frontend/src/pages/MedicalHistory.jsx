import { useMemo, useState } from 'react'
import HistoryTimeline from '../components/HistoryTimeline'
import { Alert, PageHeader, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { patientApi } from '../services/api'

export default function MedicalHistory() {
  const history = useAsync(() => patientApi.history(), [])
  const [kind, setKind] = useState('ALL')
  const entries = useMemo(
    () => (history.data?.entries || []).filter((e) => kind === 'ALL' || e.entry_type === kind),
    [history.data, kind],
  )

  return (
    <div>
      <PageHeader
        title="Medical History"
        subtitle="All your documents and healthcare records, newest first."
        actions={
          <select className="input w-auto" value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Filter history">
            <option value="ALL">Everything</option>
            <option value="DOCUMENT">Documents only</option>
            <option value="RECORD">Records only</option>
          </select>
        }
      />
      {history.loading ? <Spinner /> : history.error ? <Alert type="error">{history.error}</Alert> : <HistoryTimeline entries={entries} />}
    </div>
  )
}
