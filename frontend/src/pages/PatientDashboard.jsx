import { BookOpen, ClipboardList, FileText, Languages, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import DocumentCard from '../components/DocumentCard'
import HistoryTimeline from '../components/HistoryTimeline'
import UploadForm from '../components/UploadForm'
import { Alert, EmptyState, MedicalDisclaimer, PageHeader, Spinner, StatCard } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { contentApi, patientApi } from '../services/api'
import { formatDate, labelFor, languageLabel } from '../utils/constants'

export default function PatientDashboard() {
  const { user } = useAuth()
  const profile = useAsync(() => patientApi.me(), [])
  const docs = useAsync(() => patientApi.documents(), [])
  const history = useAsync(() => patientApi.history(), [])
  const access = useAsync(() => patientApi.accessList(), [])
  const content = useAsync(() => contentApi.list({ language: user.preferred_language }), [user.preferred_language])

  const refresh = () => { docs.reload(); history.reload() }
  const p = profile.data?.profile
  const activeGrants = access.data?.filter((g) => g.access_status === 'ACTIVE').length

  return (
    <div className="space-y-8">
      <PageHeader title={`Namaste, ${user.full_name.split(' ')[0]} 👋`} subtitle="Here is a summary of your health information." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={FileText} label="Documents" value={docs.data?.total} />
        <StatCard icon={ClipboardList} label="History entries" value={history.data?.entries.length} tone="sky" />
        <StatCard icon={Users} label="Care team members" value={activeGrants} tone="violet" />
        <StatCard icon={Languages} label="Preferred language" value={languageLabel(user.preferred_language).split(' ')[0]} tone="amber" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-1">
          <h2 className="text-lg font-semibold">Profile summary</h2>
          {profile.loading ? <Spinner /> : (
            <dl className="mt-3 space-y-2 text-sm">
              {[
                ['Name', user.full_name], ['Email', user.email || '—'], ['Phone', user.phone || '—'],
                ['Language', languageLabel(user.preferred_language)],
                ['Date of birth', formatDate(p?.date_of_birth)], ['Gender', p?.gender || '—'],
                ['Emergency contact', p?.emergency_contact_name ? `${p.emergency_contact_name} (${p.emergency_contact_phone || '—'})` : '—'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3"><dt className="text-slate-500">{k}</dt><dd className="text-right font-medium text-slate-800">{v}</dd></div>
              ))}
            </dl>
          )}
          <Link to="/profile" className="btn-secondary mt-4 w-full">Edit profile &amp; language</Link>
        </div>
        <div className="lg:col-span-2"><UploadForm uploadFn={patientApi.upload} onUploaded={refresh} /></div>
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent documents</h2>
          <Link to="/documents" className="text-sm font-semibold text-brand-700 hover:underline">View all</Link>
        </div>
        {docs.loading ? <Spinner /> : docs.error ? <Alert type="error">{docs.error}</Alert> : docs.data.items.length === 0 ? (
          <EmptyState icon={FileText} title="No documents yet">Upload your first prescription or report above.</EmptyState>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {docs.data.items.slice(0, 3).map((d) => <DocumentCard key={d.id} doc={d} onDeleted={refresh} />)}
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-semibold">Medical history</h2>
            <Link to="/history" className="text-sm font-semibold text-brand-700 hover:underline">Full history</Link>
          </div>
          {history.loading ? <Spinner /> : <HistoryTimeline entries={history.data?.entries.slice(0, 4)} />}
        </section>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-semibold">Healthcare information</h2>
            <Link to="/health-info" className="text-sm font-semibold text-brand-700 hover:underline">Browse all</Link>
          </div>
          {content.loading ? <Spinner /> : content.data?.length ? (
            <div className="space-y-3">
              {content.data.slice(0, 3).map((c) => (
                <Link key={c.id} to={`/health-info?open=${c.id}`} className="card block transition hover:border-brand-300">
                  <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">{labelFor(c.category)}</div>
                  <div className="font-semibold">{c.title}</div>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-600">{c.body}</p>
                </Link>
              ))}
              <MedicalDisclaimer />
            </div>
          ) : (
            <EmptyState icon={BookOpen} title="No articles in your language yet">
              <Link to="/health-info" className="text-brand-700 hover:underline">See articles in all languages</Link>
            </EmptyState>
          )}
        </section>
      </div>
    </div>
  )
}
