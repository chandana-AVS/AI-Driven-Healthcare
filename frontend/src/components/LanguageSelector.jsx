import { Languages } from 'lucide-react'
import { LANGUAGES } from '../utils/constants'

/** Preferred-language picker. Shows each language in its own script so users can recognise it. */
export default function LanguageSelector({ value, onChange, disabled, compact = false, id = 'language' }) {
  if (compact) {
    return (
      <select id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native} — {l.name}</option>)}
      </select>
    )
  }
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Preferred language">
      {LANGUAGES.map((l) => {
        const active = value === l.code
        return (
          <button
            key={l.code}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(l.code)}
            className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left transition ${active
              ? 'border-brand-600 bg-brand-50 ring-2 ring-brand-200'
              : 'border-slate-200 bg-white hover:border-slate-300'}`}
          >
            <Languages className={`h-4 w-4 shrink-0 ${active ? 'text-brand-700' : 'text-slate-400'}`} />
            <span>
              <span className="block text-base font-semibold leading-tight text-slate-900">{l.native}</span>
              <span className="block text-xs text-slate-500">{l.name}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
