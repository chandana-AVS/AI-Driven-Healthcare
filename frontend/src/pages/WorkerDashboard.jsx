import { BookOpen, ChevronRight, Clock, FileText, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Alert, EmptyState, PageHeader, Spinner, StatCard, StatusBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { contentApi, workerApi } from '../services/api'
import { formatDate, labelFor, languageLabel } from '../utils/constants'

export default function WorkerDashboard() {
  const { user } = useAuth()
  const profile = useAsync(() => workerApi.me(), [])
  const verified = profile.data?.profile.verification_status === 'VERIFIED'
  const patients = useAsync(() => (verified ? workerApi.patients() : Promise.resolve({ data: [] })), [verified])
  const content = useAsync(() => contentApi.list(), [])

  if (profile.loading) return <Spinner />
  if (profile.error) return <Alert type="error">{profile.error}</Alert>
  const p = profile.data.profile
  const totalDocs = patients.data?.reduce((s, x) => s + x.document_count, 0)

  return (
    <div className="space-y-8">
      <PageHeader title={`Welcome, ${user.full_name}`} subtitle={[p.designation, p.organization].filter(Boolean).join(' · ')} />

      {p.verification_status === 'PENDING' && (
        <Alert type="warning">
          Your account is awaiting administrator verification. Once verified, patients can grant you access to their records.
        </Alert>
      )}
      {p.verification_status === 'REJECTED' && (
        <Alert type="error">Your verification request was rejected. Please contact the administrator.</Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={Users} label="Authorized patients" value={verified ? patients.data?.length : 0} />
        <StatCard icon={FileText} label="Documents across patients" value={verified ? totalDocs : 0} tone="sky" />
        <div className="card flex items-center gap-4">
          <div className="rounded-xl bg-violet-50 p-3 text-violet-700"><Clock className="h-6 w-6" /></div>
          <div><div className="mb-1"><StatusBadge status={p.verification_status} /></div><div className="text-sm text-slate-500">Verification status</div></div>
        </div>
      </div>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Authorized patients</h2>
        {!verified ? (
          <EmptyState icon={Users} title="Not available yet">You can view patients after your account is verified.</EmptyState>
        ) : patients.loading ? <Spinner /> : patients.error ? <Alert type="error">{patients.error}</Alert> : patients.data.length === 0 ? (
          <EmptyState icon={Users} title="No patients have granted you access">Ask patients to add you from their “Care Team” page.</EmptyState>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {patients.data.map((pt) => (
              <Link key={pt.patient_id} to={`/worker/patients/${pt.patient_id}`} className="flex items-center gap-4 border-b border-slate-100 px-5 py-4 transition last:border-0 hover:bg-slate-50">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-800">{pt.full_name[0]}</div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold">{pt.full_name}</div>
                  <div className="text-sm text-slate-500">
                    {[pt.gender, pt.date_of_birth && `Born ${formatDate(pt.date_of_birth)}`, languageLabel(pt.preferred_language)].filter(Boolean).join(' · ')}
                  </div>
                </div>
                <div className="hidden text-right text-sm text-slate-500 sm:block">
                  {pt.document_count} docs · {pt.record_count} records<div className="text-xs">Access since {formatDate(pt.access_granted_at)}</div>
                </div>
                <ChevronRight className="h-5 w-5 text-slate-400" />
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Healthcare information repository</h2>
          <Link to="/health-info" className="text-sm font-semibold text-brand-700 hover:underline">Browse all</Link>
        </div>
        {content.loading ? <Spinner /> : content.data?.length ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {content.data.slice(0, 3).map((c) => (
              <Link key={c.id} to={`/health-info?open=${c.id}`} className="card block hover:border-brand-300">
                <div className="text-xs font-semibold uppercase text-brand-700">{labelFor(c.category)}</div>
                <div className="font-semibold">{c.title}</div>
              </Link>
            ))}
          </div>
        ) : <EmptyState icon={BookOpen} title="No published content yet" />}
      </section>
    </div>
  )
}
