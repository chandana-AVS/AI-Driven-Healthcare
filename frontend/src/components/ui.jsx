import { AlertCircle, CheckCircle2, Info, Loader2 } from 'lucide-react'

export function Spinner({ label = 'Loading…', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-2 py-10 text-slate-500 ${className}`} role="status">
      <Loader2 className="h-5 w-5 animate-spin" /> <span>{label}</span>
    </div>
  )
}

const ALERT_STYLES = {
  error: ['border-red-200 bg-red-50 text-red-800', AlertCircle],
  success: ['border-emerald-200 bg-emerald-50 text-emerald-800', CheckCircle2],
  info: ['border-sky-200 bg-sky-50 text-sky-800', Info],
  warning: ['border-amber-200 bg-amber-50 text-amber-900', AlertCircle],
}

export function Alert({ type = 'info', children, className = '' }) {
  if (!children) return null
  const [style, Icon] = ALERT_STYLES[type]
  return (
    <div className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${style} ${className}`} role="alert">
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  )
}

const BADGE_STYLES = {
  green: 'bg-emerald-100 text-emerald-800',
  yellow: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-800',
  gray: 'bg-slate-100 text-slate-700',
  blue: 'bg-sky-100 text-sky-800',
  teal: 'bg-brand-100 text-brand-800',
}

export function Badge({ color = 'gray', children }) {
  return <span className={`badge ${BADGE_STYLES[color]}`}>{children}</span>
}

export const STATUS_COLOR = {
  VERIFIED: 'green', PUBLISHED: 'green', ACTIVE: 'green', UPLOADED: 'teal', PROCESSED: 'green',
  PENDING: 'yellow', DRAFT: 'yellow', QUEUED: 'yellow', PROCESSING: 'blue',
  REJECTED: 'red', REVOKED: 'red', INACTIVE: 'gray', FAILED: 'red',
}

export function StatusBadge({ status }) {
  return <Badge color={STATUS_COLOR[status] || 'gray'}>{status?.replaceAll('_', ' ')}</Badge>
}

export function StatCard({ icon: Icon, label, value, tone = 'brand' }) {
  const tones = {
    brand: 'bg-brand-50 text-brand-700', amber: 'bg-amber-50 text-amber-700',
    sky: 'bg-sky-50 text-sky-700', violet: 'bg-violet-50 text-violet-700',
  }
  return (
    <div className="card flex items-center gap-4">
      <div className={`rounded-xl p-3 ${tones[tone]}`}><Icon className="h-6 w-6" /></div>
      <div>
        <div className="text-2xl font-bold text-slate-900">{value ?? '—'}</div>
        <div className="text-sm text-slate-500">{label}</div>
      </div>
    </div>
  )
}

export function EmptyState({ icon: Icon, title, children }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
      {Icon && <Icon className="mb-3 h-10 w-10 text-slate-300" />}
      <div className="font-semibold text-slate-700">{title}</div>
      {children && <div className="mt-1 text-sm text-slate-500">{children}</div>}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Field({ label, error, children, hint }) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

export function MedicalDisclaimer() {
  return (
    <p className="text-xs text-slate-500">
      This information is for general health education and does not replace advice from a qualified
      healthcare professional. In an emergency, contact your nearest health centre immediately.
    </p>
  )
}
