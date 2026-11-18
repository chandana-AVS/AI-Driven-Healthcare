import { BookOpen, ChevronDown, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Alert, EmptyState, MedicalDisclaimer, PageHeader, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { contentApi } from '../services/api'
import { CONTENT_CATEGORIES, LANGUAGES, formatDate, labelFor, languageLabel } from '../utils/constants'

const TYPE_TABS = [['', 'All'], ['FAQ', 'FAQs'], ['DISEASE_INFO', 'Diseases'], ['ARTICLE', 'Articles']]

function Faq({ item }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card">
      <button className="flex w-full items-start justify-between gap-4 text-left" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="font-semibold">{item.title}</span>
        <ChevronDown className={`mt-1 h-5 w-5 shrink-0 text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="mt-3 whitespace-pre-line leading-relaxed text-slate-700">{item.body}</div>}
      <div className="mt-2 text-xs text-slate-400">{languageLabel(item.language_code)}</div>
    </div>
  )
}

export default function HealthInfo() {
  const [params, setParams] = useSearchParams()
  const [type, setType] = useState('')
  const [category, setCategory] = useState('')
  const [language, setLanguage] = useState('')
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  useEffect(() => { const t = setTimeout(() => setQuery(search.trim()), 350); return () => clearTimeout(t) }, [search])

  const content = useAsync(
    () => contentApi.list({ ...(type && { content_type: type }), ...(category && { category }), ...(language && { language }), ...(query && { search: query }) }),
    [type, category, language, query],
  )
  const openId = params.get('open')
  const [open, setOpen] = useState(null)
  const [versions, setVersions] = useState([])
  useEffect(() => {
    if (!openId) { setOpen(null); return }
    contentApi.get(openId).then(({ data }) => setOpen(data)).catch(() => setOpen(null))
    contentApi.translations(openId).then(({ data }) => setVersions(data)).catch(() => setVersions([]))
  }, [openId])

  const faqs = content.data?.filter((c) => c.content_type === 'FAQ') || []
  const cards = content.data?.filter((c) => c.content_type !== 'FAQ') || []

  return (
    <div className="space-y-6">
      <PageHeader title="Health Knowledge Base" subtitle="Answers to common questions, information about common diseases and health awareness articles." />
      <div className="flex flex-wrap gap-1 rounded-2xl bg-slate-100 p-1">
        {TYPE_TABS.map(([key, label]) => (
          <button key={key} onClick={() => setType(key)}
            className={`flex-1 rounded-xl px-3 py-2 text-sm font-semibold transition ${type === key ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>{label}</button>
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Search e.g. fever, ORS, diabetes" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="input w-auto" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {CONTENT_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select className="input w-auto" value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Language">
          <option value="">All languages</option>
          {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native} — {l.name}</option>)}
        </select>
      </div>

      {content.loading ? <Spinner /> : content.error ? <Alert type="error">{content.error}</Alert> : content.data.length === 0 ? (
        <EmptyState icon={BookOpen} title="Nothing found">Try another search, type or language.</EmptyState>
      ) : (
        <>
          {faqs.length > 0 && (
            <section className="space-y-3">
              {type === '' && <h2 className="text-lg font-semibold">Frequently asked questions</h2>}
              {faqs.map((f) => <Faq key={f.id} item={f} />)}
            </section>
          )}
          {cards.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {cards.map((c) => (
                <button key={c.id} onClick={() => setParams({ open: c.id })} className="card text-left transition hover:border-brand-300 hover:shadow">
                  <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">{labelFor(c.content_type)} · {labelFor(c.category)}</div>
                  <div className="mt-1 font-semibold">{c.title}</div>
                  <p className="mt-2 line-clamp-3 text-sm text-slate-600">{c.body}</p>
                  <div className="mt-3 text-xs text-slate-400">{languageLabel(c.language_code)}</div>
                </button>
              ))}
            </div>
          )}
        </>
      )}
      <MedicalDisclaimer />

      {open && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/50 p-4" onClick={() => setParams({})}>
          <article className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">{labelFor(open.content_type)} · {labelFor(open.category)}</div>
                <h2 className="mt-1 text-2xl font-bold">{open.title}</h2>
                <div className="mt-1 text-xs text-slate-500">{languageLabel(open.language_code)} · {formatDate(open.updated_at)}</div>
              </div>
              <button className="btn-ghost p-2" onClick={() => setParams({})} aria-label="Close"><X className="h-5 w-5" /></button>
            </div>
            {versions.length > 1 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {versions.map((v) => (
                  <button key={v.id} onClick={() => setParams({ open: v.id })}
                    className={`badge ${v.id === open.id ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}>
                    {LANGUAGES.find((l) => l.code === v.language_code)?.native || v.language_code}
                  </button>
                ))}
              </div>
            )}
            <div className="mt-4 whitespace-pre-line text-base leading-relaxed text-slate-700">{open.body}</div>
            <div className="mt-6 border-t border-slate-100 pt-4"><MedicalDisclaimer /></div>
          </article>
        </div>
      )}
    </div>
  )
}
