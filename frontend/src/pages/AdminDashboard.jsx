import { BookOpen, CheckCircle2, Clock, FileText, Languages, Pencil, Plus, ShieldOff, Stethoscope, Trash2, UserCheck, Users, X, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Alert, EmptyState, Field, PageHeader, Spinner, StatCard, StatusBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { adminApi, errorMessage } from '../services/api'
import { CONTENT_CATEGORIES, CONTENT_TYPES, LANGUAGES, formatDate, formatDateTime, labelFor, languageLabel } from '../utils/constants'

const TABS = [['overview', 'Overview'], ['users', 'Users'], ['content', 'Content'], ['access', 'Access grants'], ['audit', 'Activity log']]

function Table({ head, children }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>{head.map((h) => <th key={h} className="whitespace-nowrap px-4 py-3">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  )
}

function useAction() {
  const [msg, setMsg] = useState({ type: '', text: '' })
  const [busy, setBusy] = useState('')
  const run = async (key, fn, ok) => {
    setBusy(key); setMsg({ type: '', text: '' })
    try { await fn(); if (ok) setMsg({ type: 'success', text: ok }) } catch (err) { setMsg({ type: 'error', text: errorMessage(err) }) } finally { setBusy('') }
  }
  return { msg, busy, run }
}

// ------------------------------------------------------------------------------------------------ Users
function UsersPanel({ initialFilter = {}, onChanged }) {
  const { user: me } = useAuth()
  const [role, setRole] = useState(initialFilter.role || '')
  const [vstatus, setVstatus] = useState(initialFilter.verification_status || '')
  const [search, setSearch] = useState('')
  const users = useAsync(() => adminApi.users({
    ...(role && { role }), ...(vstatus && { verification_status: vstatus }), ...(search && { search }),
  }), [role, vstatus, search])
  const { msg, busy, run } = useAction()

  const verify = (u, status) => run(u.id, async () => {
    if (u.admin_profile) await adminApi.setAdminVerification(u.admin_profile.id, status)
    else await adminApi.setVerification(u.worker_profile.id, status)
    users.reload(); onChanged?.()
  }, `${u.full_name} marked ${status.toLowerCase()}.`)
  const toggleActive = (u) => run(u.id, async () => {
    await adminApi.setUserStatus(u.id, !u.is_active); users.reload(); onChanged?.()
  }, `${u.full_name} ${u.is_active ? 'deactivated' : 'activated'}.`)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <select className="input w-auto" value={role} onChange={(e) => setRole(e.target.value)} aria-label="Role">
          <option value="">All roles</option><option value="PATIENT">Patients</option><option value="HEALTHCARE_WORKER">Healthcare workers</option><option value="ADMIN">Admins</option>
        </select>
        <select className="input w-auto" value={vstatus} onChange={(e) => setVstatus(e.target.value)} aria-label="Verification">
          <option value="">Any verification</option><option value="PENDING">Pending</option><option value="VERIFIED">Verified</option><option value="REJECTED">Rejected</option>
        </select>
        <input className="input max-w-xs" placeholder="Search name, email, phone" onChange={(e) => setSearch(e.target.value.trim())} />
      </div>
      <Alert type={msg.type || 'info'}>{msg.text}</Alert>
      {users.loading ? <Spinner /> : users.error ? <Alert type="error">{users.error}</Alert> : users.data.length === 0 ? (
        <EmptyState icon={Users} title="No users match these filters" />
      ) : (
        <Table head={['Name', 'Role', 'Contact', 'Language', 'Verification', 'Status', 'Joined', 'Actions']}>
          {users.data.map((u) => {
            const vp = u.worker_profile || u.admin_profile
            const canVerify = vp && u.id !== me.id
            return (
            <tr key={u.id} className={u.is_active ? '' : 'bg-slate-50 text-slate-400'}>
              <td className="px-4 py-3">
                <div className="font-medium text-slate-900">{u.full_name}</div>
                {u.worker_profile && <div className="text-xs text-slate-500">{u.worker_profile.designation} · {u.worker_profile.organization}</div>}
                {u.admin_profile && <div className="text-xs text-slate-500">Emp ID {u.admin_profile.employee_id} · {u.admin_profile.hospital_name}</div>}
              </td>
              <td className="px-4 py-3 text-xs">{labelFor(u.role)}</td>
              <td className="px-4 py-3 text-xs">{u.email}<div>{u.phone}</div></td>
              <td className="px-4 py-3 text-xs">{languageLabel(u.preferred_language)}</td>
              <td className="px-4 py-3">{vp ? <StatusBadge status={vp.verification_status} /> : '—'}</td>
              <td className="px-4 py-3"><StatusBadge status={u.is_active ? 'ACTIVE' : 'INACTIVE'} /></td>
              <td className="whitespace-nowrap px-4 py-3 text-xs">{formatDate(u.created_at)}</td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-1">
                  {canVerify && vp.verification_status !== 'VERIFIED' && (
                    <button className="btn-ghost px-2 py-1.5 text-emerald-700 hover:bg-emerald-50" disabled={busy === u.id} onClick={() => verify(u, 'VERIFIED')} title="Verify">
                      <CheckCircle2 className="h-4 w-4" />{u.admin_profile ? 'Approve' : 'Verify'}
                    </button>
                  )}
                  {canVerify && vp.verification_status !== 'REJECTED' && (
                    <button className="btn-ghost px-2 py-1.5 text-red-600 hover:bg-red-50" disabled={busy === u.id} onClick={() => verify(u, 'REJECTED')} title="Reject">
                      <XCircle className="h-4 w-4" />
                    </button>
                  )}
                  {u.id !== me.id && (
                    <button className="btn-ghost px-2 py-1.5 text-xs" disabled={busy === u.id} onClick={() => toggleActive(u)}>
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                </div>
              </td>
            </tr>
            )
          })}
        </Table>
      )}
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ Content
const EMPTY_CONTENT = { title: '', body: '', category: 'GENERAL_HEALTH', content_type: 'ARTICLE', language_code: 'en', status: 'DRAFT' }

function ContentEditor({ initial, onCancel, onSaved }) {
  const [form, setForm] = useState(initial ? {
    title: initial.title, body: initial.body, category: initial.category, content_type: initial.content_type, language_code: initial.language_code, status: initial.status,
  } : EMPTY_CONTENT)
  const { msg, busy, run } = useAction()
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const save = (e) => {
    e.preventDefault()
    run('save', async () => {
      if (initial) await adminApi.updateContent(initial.id, form)
      else await adminApi.createContent(form)
      onSaved()
    })
  }
  return (
    <form onSubmit={save} className="card space-y-4 border-brand-200">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{initial ? 'Edit content' : 'New content'}</h3>
        <button type="button" className="btn-ghost p-2" onClick={onCancel} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <Field label="Title"><input className="input" value={form.title} onChange={set('title')} minLength={3} maxLength={255} required /></Field>
      <div className="grid gap-4 sm:grid-cols-4">
        <Field label="Type">
          <select className="input" value={form.content_type} onChange={set('content_type')}>
            {CONTENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </Field>
        <Field label="Category">
          <select className="input" value={form.category} onChange={set('category')}>
            {CONTENT_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </Field>
        <Field label="Language">
          <select className="input" value={form.language_code} onChange={set('language_code')}>
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native} — {l.name}</option>)}
          </select>
        </Field>
        <Field label="Status">
          <select className="input" value={form.status} onChange={set('status')}>
            <option value="DRAFT">Draft</option><option value="PUBLISHED">Published</option><option value="INACTIVE">Inactive</option>
          </select>
        </Field>
      </div>
      <Field label="Body" hint="Publish only content reviewed by a qualified healthcare professional.">
        <textarea className="input min-h-40" value={form.body} onChange={set('body')} minLength={10} required />
      </Field>
      <Alert type={msg.type}>{msg.text}</Alert>
      <button className="btn-primary" disabled={busy === 'save'}>{busy === 'save' ? 'Saving…' : 'Save content'}</button>
    </form>
  )
}

function TranslateDialog({ item, onClose, onDone }) {
  const [langs, setLangs] = useState(LANGUAGES.filter((l) => l.code !== item.language_code).map((l) => l.code))
  const { msg, busy, run } = useAction()
  const toggle = (code) => setLangs((xs) => (xs.includes(code) ? xs.filter((x) => x !== code) : [...xs, code]))
  const go = () => run('tr', async () => {
    const { data } = await adminApi.translateContent(item.id, langs)
    onDone(`Created ${data.length} draft translation(s). Review them, then publish.`)
  })
  return (
    <div className="card space-y-4 border-brand-200">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Translate “{item.title}” with AI</h3>
        <button type="button" className="btn-ghost p-2" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
      </div>
      <div className="flex flex-wrap gap-3">
        {LANGUAGES.filter((l) => l.code !== item.language_code).map((l) => (
          <label key={l.code} className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm">
            <input type="checkbox" checked={langs.includes(l.code)} onChange={() => toggle(l.code)} />{l.native} — {l.name}
          </label>
        ))}
      </div>
      <p className="text-xs text-slate-500">Translations are saved as drafts. A person who reads the language should check them before publishing.</p>
      <Alert type={msg.type}>{msg.text}</Alert>
      <button className="btn-primary" disabled={busy === 'tr' || langs.length === 0} onClick={go}>
        <Languages className="h-4 w-4" />{busy === 'tr' ? 'Translating… (up to a minute)' : `Translate into ${langs.length} language(s)`}
      </button>
    </div>
  )
}

function ContentPanel({ onChanged }) {
  const [statusFilter, setStatusFilter] = useState('')
  const content = useAsync(() => adminApi.content(statusFilter ? { status: statusFilter } : undefined), [statusFilter])
  const [editing, setEditing] = useState(null) // null | 'new' | item
  const [translating, setTranslating] = useState(null)
  const { msg, busy, run } = useAction()
  const reload = () => { content.reload(); onChanged?.() }

  const setStatus = (c, status) => run(c.id, async () => { await adminApi.updateContent(c.id, { status }); reload() },
    `"${c.title}" is now ${status.toLowerCase()}.`)
  const remove = (c) => {
    if (!window.confirm(`Delete "${c.title}" permanently?`)) return
    run(c.id, async () => { await adminApi.deleteContent(c.id); reload() }, 'Content deleted.')
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <select className="input w-auto" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Status filter">
          <option value="">All statuses</option><option value="DRAFT">Draft</option><option value="PUBLISHED">Published</option><option value="INACTIVE">Inactive</option>
        </select>
        <button className="btn-primary" onClick={() => setEditing('new')}><Plus className="h-4 w-4" />New content</button>
      </div>
      {editing && (
        <ContentEditor key={editing === 'new' ? 'new' : editing.id} initial={editing === 'new' ? null : editing}
          onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); reload() }} />
      )}
      {translating && (
        <TranslateDialog key={translating.id} item={translating} onClose={() => setTranslating(null)}
          onDone={(text) => { setTranslating(null); reload(); run('note', async () => {}, text) }} />
      )}
      <Alert type={msg.type || 'info'}>{msg.text}</Alert>
      {content.loading ? <Spinner /> : content.error ? <Alert type="error">{content.error}</Alert> : content.data.length === 0 ? (
        <EmptyState icon={BookOpen} title="No content yet">Create an article, or run <code>python -m scripts.seed_content</code>.</EmptyState>
      ) : (
        <Table head={['Title', 'Type', 'Category', 'Language', 'Status', 'Updated', 'Actions']}>
          {content.data.map((c) => (
            <tr key={c.id}>
              <td className="px-4 py-3 font-medium">{c.title}</td>
              <td className="px-4 py-3 text-xs">{labelFor(c.content_type)}</td>
              <td className="px-4 py-3 text-xs">{labelFor(c.category)}</td>
              <td className="px-4 py-3 text-xs">{languageLabel(c.language_code)}</td>
              <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
              <td className="whitespace-nowrap px-4 py-3 text-xs">{formatDate(c.updated_at)}</td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-1">
                  {c.status !== 'PUBLISHED'
                    ? <button className="btn-ghost px-2 py-1.5 text-xs text-emerald-700" disabled={busy === c.id} onClick={() => setStatus(c, 'PUBLISHED')}>Publish</button>
                    : <button className="btn-ghost px-2 py-1.5 text-xs" disabled={busy === c.id} onClick={() => setStatus(c, 'INACTIVE')}>Deactivate</button>}
                  <button className="btn-ghost p-2 text-brand-700" onClick={() => { setEditing(null); setTranslating(c) }} aria-label="Translate" title="Translate with AI"><Languages className="h-4 w-4" /></button>
                  <button className="btn-ghost p-2" onClick={() => setEditing(c)} aria-label="Edit"><Pencil className="h-4 w-4" /></button>
                  <button className="btn-ghost p-2 text-red-600 hover:bg-red-50" disabled={busy === c.id} onClick={() => remove(c)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
                </div>
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ Access
function AccessPanel() {
  const grants = useAsync(() => adminApi.access(), [])
  const { msg, busy, run } = useAction()
  const revoke = (g) => {
    if (!window.confirm(`Revoke ${g.worker_name}'s access to ${g.patient_name}?`)) return
    run(g.id, async () => { await adminApi.revokeAccess(g.id); grants.reload() }, 'Access revoked.')
  }
  return (
    <div className="space-y-4">
      <Alert type="info">Patients grant access from their Care Team page. Administrators can review and revoke grants here.</Alert>
      <Alert type={msg.type || 'info'}>{msg.text}</Alert>
      {grants.loading ? <Spinner /> : grants.error ? <Alert type="error">{grants.error}</Alert> : grants.data.length === 0 ? (
        <EmptyState icon={UserCheck} title="No access grants yet" />
      ) : (
        <Table head={['Patient', 'Healthcare worker', 'Status', 'Granted', 'Revoked', '']}>
          {grants.data.map((g) => (
            <tr key={g.id}>
              <td className="px-4 py-3 font-medium">{g.patient_name}</td>
              <td className="px-4 py-3">{g.worker_name}<div className="text-xs text-slate-500">{g.worker_organization}</div></td>
              <td className="px-4 py-3"><StatusBadge status={g.access_status} /></td>
              <td className="whitespace-nowrap px-4 py-3 text-xs">{formatDateTime(g.created_at)}</td>
              <td className="whitespace-nowrap px-4 py-3 text-xs">{formatDateTime(g.revoked_at)}</td>
              <td className="px-4 py-3 text-right">
                {g.access_status === 'ACTIVE' && (
                  <button className="btn-ghost px-2 py-1.5 text-xs text-red-600 hover:bg-red-50" disabled={busy === g.id} onClick={() => revoke(g)}>
                    <ShieldOff className="h-4 w-4" />Revoke
                  </button>
                )}
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ Audit
function AuditPanel() {
  const logs = useAsync(() => adminApi.auditLogs({ limit: 200 }), [])
  if (logs.loading) return <Spinner />
  if (logs.error) return <Alert type="error">{logs.error}</Alert>
  return (
    <Table head={['Time', 'User', 'Action', 'Resource', 'IP']}>
      {logs.data.map((l) => (
        <tr key={l.id}>
          <td className="whitespace-nowrap px-4 py-2.5 text-xs">{formatDateTime(l.created_at)}</td>
          <td className="px-4 py-2.5">{l.actor_name || <span className="text-slate-400">anonymous</span>}</td>
          <td className="px-4 py-2.5"><code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{l.action}</code></td>
          <td className="px-4 py-2.5 text-xs">{labelFor(l.resource_type)}</td>
          <td className="px-4 py-2.5 text-xs text-slate-500">{l.ip_address || '—'}</td>
        </tr>
      ))}
    </Table>
  )
}

// ------------------------------------------------------------------------------------------------ Pending approval
function PendingApproval() {
  const { refreshUser } = useAuth()
  const me = useAsync(() => adminApi.me(), [])
  const [checking, setChecking] = useState(false)
  const recheck = async () => {
    setChecking(true)
    try { await refreshUser(); await me.reload() } finally { setChecking(false) }
  }
  if (me.loading) return <Spinner />
  if (me.error) return <Alert type="error">{me.error}</Alert>
  const { profile, verification_status: vs } = me.data
  return (
    <div className="mx-auto max-w-xl">
      <div className="card p-7 text-center">
        <Clock className={`mx-auto mb-3 h-12 w-12 ${vs === 'REJECTED' ? 'text-red-500' : 'text-amber-500'}`} />
        <h1 className="text-2xl font-bold">{vs === 'REJECTED' ? 'Registration rejected' : 'Awaiting approval'}</h1>
        <p className="mt-2 text-slate-600">
          {vs === 'REJECTED'
            ? 'An administrator could not verify your details. Please contact your hospital administration.'
            : 'An existing administrator must verify your employee ID with your hospital before you can use the admin dashboard.'}
        </p>
        {profile && (
          <dl className="mx-auto mt-5 max-w-xs space-y-1 text-left text-sm">
            <div className="flex justify-between"><dt className="text-slate-500">Employee ID</dt><dd className="font-medium">{profile.employee_id}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-slate-500">Hospital</dt><dd className="text-right font-medium">{profile.hospital_name}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Status</dt><dd><StatusBadge status={vs} /></dd></div>
          </dl>
        )}
        {vs !== 'REJECTED' && (
          <button className="btn-secondary mt-6" onClick={recheck} disabled={checking}>{checking ? 'Checking…' : 'Check again'}</button>
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------------------------------------ Page
export default function AdminDashboard() {
  const { user } = useAuth()
  return user.is_verified ? <AdminConsole /> : <PendingApproval />
}

function AdminConsole() {
  const [tab, setTab] = useState('overview')
  const stats = useAsync(() => adminApi.stats(), [])
  const s = stats.data
  const pendingTotal = (s?.pending_verifications || 0) + (s?.pending_admin_verifications || 0)

  return (
    <div className="space-y-6">
      <PageHeader title="Administrator Dashboard" subtitle="Manage users, verify healthcare workers and curate healthcare content." />
      <div className="flex gap-1 overflow-x-auto rounded-2xl bg-slate-100 p-1">
        {TABS.map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold transition ${tab === key ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600'}`}>
            {label}{key === 'overview' && pendingTotal > 0 && <span className="ml-1.5 rounded-full bg-amber-500 px-1.5 text-xs text-white">{pendingTotal}</span>}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          {stats.error && <Alert type="error">{stats.error}</Alert>}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={Users} label="Registered patients" value={s?.total_patients} />
            <StatCard icon={Stethoscope} label="Healthcare workers" value={s?.total_healthcare_workers} tone="sky" />
            <StatCard icon={UserCheck} label="Pending verifications (workers / admins)" value={s ? `${s.pending_verifications} / ${s.pending_admin_verifications}` : null} tone="amber" />
            <StatCard icon={FileText} label="Documents stored" value={s?.total_documents} tone="violet" />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard icon={CheckCircle2} label="Verified workers" value={s?.verified_workers} />
            <StatCard icon={UserCheck} label="Active access grants" value={s?.active_access_grants} tone="sky" />
            <StatCard icon={BookOpen} label="Published / total content" value={s ? `${s.published_content} / ${s.total_content}` : null} tone="amber" />
          </div>
          <section>
            <h2 className="mb-3 text-xl font-semibold">Healthcare workers &amp; admins awaiting verification</h2>
            <UsersPanel key="pending" initialFilter={{ verification_status: 'PENDING' }} onChanged={stats.reload} />
          </section>
        </div>
      )}
      {tab === 'users' && <UsersPanel onChanged={stats.reload} />}
      {tab === 'content' && <ContentPanel onChanged={stats.reload} />}
      {tab === 'access' && <AccessPanel />}
      {tab === 'audit' && <AuditPanel />}
    </div>
  )
}
