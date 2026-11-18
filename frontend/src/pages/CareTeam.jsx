import { Search, ShieldCheck, ShieldOff, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { Alert, EmptyState, PageHeader, Spinner, StatusBadge } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { errorMessage, patientApi } from '../services/api'
import { formatDate } from '../utils/constants'

/** Patients explicitly grant and revoke healthcare-worker access to their records. */
export default function CareTeam() {
  const grants = useAsync(() => patientApi.accessList(), [])
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const directory = useAsync(() => patientApi.workerDirectory(query || undefined), [query])
  const [message, setMessage] = useState({ type: '', text: '' })
  const [busyId, setBusyId] = useState('')

  const activeIds = new Set((grants.data || []).filter((g) => g.access_status === 'ACTIVE').map((g) => g.healthcare_worker_id))

  const act = async (id, fn, ok) => {
    setBusyId(id); setMessage({ type: '', text: '' })
    try { await fn(); setMessage({ type: 'success', text: ok }); grants.reload() }
    catch (err) { setMessage({ type: 'error', text: errorMessage(err) }) }
    finally { setBusyId('') }
  }

  const grant = (w) => act(w.healthcare_worker_id, () => patientApi.grantAccess({ healthcare_worker_id: w.healthcare_worker_id }),
    `${w.full_name} can now see your records.`)
  const revoke = (g) => {
    if (!window.confirm(`Remove ${g.worker_name}'s access to your records?`)) return
    act(g.id, () => patientApi.revokeAccess(g.id), `${g.worker_name} no longer has access.`)
  }

  return (
    <div className="space-y-8">
      <PageHeader title="My Care Team" subtitle="Choose which verified healthcare workers can view and manage your medical records." />
      <Alert type={message.type || 'info'}>{message.text}</Alert>

      <section>
        <h2 className="mb-3 text-xl font-semibold">People with access</h2>
        {grants.loading ? <Spinner /> : grants.error ? <Alert type="error">{grants.error}</Alert> : grants.data.length === 0 ? (
          <EmptyState icon={Users} title="No one has access yet">Only you can see your records right now.</EmptyState>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr><th className="px-4 py-3">Healthcare worker</th><th className="px-4 py-3">Organization</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Granted</th><th className="px-4 py-3" /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {grants.data.map((g) => (
                  <tr key={g.id}>
                    <td className="px-4 py-3"><div className="font-medium">{g.worker_name}</div><div className="text-xs text-slate-500">{g.worker_designation}</div></td>
                    <td className="px-4 py-3">{g.worker_organization || '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={g.access_status} /></td>
                    <td className="px-4 py-3">{formatDate(g.created_at)}{g.revoked_at && <div className="text-xs text-slate-500">Revoked {formatDate(g.revoked_at)}</div>}</td>
                    <td className="px-4 py-3 text-right">
                      {g.access_status === 'ACTIVE' && (
                        <button className="btn-ghost px-3 py-1.5 text-red-600 hover:bg-red-50" disabled={busyId === g.id} onClick={() => revoke(g)}>
                          <ShieldOff className="h-4 w-4" />Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <h2 className="text-xl font-semibold">Add a healthcare worker</h2>
        <p className="mt-1 text-sm text-slate-500">Only administrator-verified healthcare workers are listed.</p>
        <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); setQuery(search.trim()) }}>
          <input className="input" placeholder="Search by name or organization" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button className="btn-secondary"><Search className="h-4 w-4" />Search</button>
        </form>
        <div className="mt-4 divide-y divide-slate-100">
          {directory.loading ? <Spinner /> : directory.error ? <Alert type="error">{directory.error}</Alert> : directory.data.length === 0 ? (
            <p className="py-4 text-sm text-slate-500">No verified healthcare workers found.</p>
          ) : directory.data.map((w) => (
            <div key={w.healthcare_worker_id} className="flex items-center justify-between gap-3 py-3">
              <div>
                <div className="font-medium">{w.full_name}</div>
                <div className="text-sm text-slate-500">{[w.designation, w.organization].filter(Boolean).join(' · ')}</div>
              </div>
              {activeIds.has(w.healthcare_worker_id) ? (
                <span className="flex items-center gap-1 text-sm font-medium text-emerald-700"><ShieldCheck className="h-4 w-4" />Has access</span>
              ) : (
                <button className="btn-primary px-3 py-2" disabled={busyId === w.healthcare_worker_id} onClick={() => grant(w)}>
                  <UserPlus className="h-4 w-4" />Grant access
                </button>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
