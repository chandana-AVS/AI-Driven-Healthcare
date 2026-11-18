import { HeartPulse, Languages, Lightbulb, ListChecks, MessageCircleQuestion, Search, ShieldCheck, Sparkles, Stethoscope } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AiDisclaimer, AiStatusNotice, BulletList, EntitiesView, Glossary, LanguageSelect, RelatedContent, ResultActions, Section,
  UrgencyBanner, WarningSigns,
} from '../components/ai'
import { Alert, Field, PageHeader, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useSessionState } from '../hooks/useSessionState'
import { aiApi, errorMessage } from '../services/api'
import { TEXT_TYPES } from '../utils/constants'

const NL = String.fromCharCode(10)

const TABS = [
  ['translate', 'Translate', Languages],
  ['simplify', 'Explain simply', Lightbulb],
  ['extract', 'Find medicines & diseases', Search],
  ['symptoms', 'Symptom helper', Stethoscope],
]

// The last result of each tool is kept for this browser tab, so it is still there after pressing Back.
function useAiCall(fn, key) {
  const { user } = useAuth()
  const [data, setData] = useSessionState(`${user.id}:${key}:result`, null)
  const [state, setState] = useState({ busy: false, error: '' })
  const run = async (payload) => {
    setState({ busy: true, error: '' })
    setData(null)
    try {
      const { data: result } = await fn(payload)
      setData({ ...result, _language: payload.target_language || payload.language })
      setState({ busy: false, error: '' })
    } catch (err) {
      setState({ busy: false, error: errorMessage(err, 'The AI request failed.') })
    }
  }
  return [{ ...state, data }, run]
}

function useDraft(key, initial) {
  const { user } = useAuth()
  return useSessionState(`${user.id}:${key}:draft`, initial)
}

function TextInput({ value, onChange, placeholder }) {
  return (
    <Field label="Medical text" hint="Type or paste the text from a prescription, discharge summary or instruction sheet">
      <textarea className="input min-h-40" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} maxLength={20000} />
    </Field>
  )
}

const SAMPLE = 'Tab. Amlodipine 5 mg OD x 30 days\nTab. Metformin 500 mg BD PC\nLow salt diet. Review after 1 month with FBS report.'

function TranslatePanel({ language, setLanguage }) {
  const [text, setText] = useDraft('translate', '')
  const [textType, setTextType] = useDraft('translate-type', 'PRESCRIPTION')
  const [state, run] = useAiCall(aiApi.translate, 'translate')
  const r = state.data
  return (
    <div className="space-y-5">
      <form className="card space-y-4" onSubmit={(e) => { e.preventDefault(); run({ text, target_language: language, text_type: textType }) }}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Type of text">
            <select className="input" value={textType} onChange={(e) => setTextType(e.target.value)}>
              {TEXT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>
          <LanguageSelect label="Translate into" value={language} onChange={setLanguage} />
        </div>
        <TextInput value={text} onChange={setText} placeholder={SAMPLE} />
        <SubmitRow busy={state.busy} disabled={text.trim().length < 2} label="Translate" onSample={() => setText(SAMPLE)} />
      </form>
      <Alert type="error">{state.error}</Alert>
      {state.busy && <Spinner label="Translating…" />}
      {r && (
        <>
          <ResultActions language={r._language || language} text={`${r.simplified}

${r.translation}`} />
          <Section icon={Sparkles} title="Simple version"><p className="whitespace-pre-line text-lg leading-relaxed">{r.simplified}</p></Section>
          <Section icon={ListChecks} title="Key points"><BulletList items={r.key_points} /></Section>
          <Section icon={Languages} title="Full translation"><p className="whitespace-pre-line leading-relaxed">{r.translation}</p></Section>
          <Glossary terms={r.glossary} />
          <AiDisclaimer />
        </>
      )}
    </div>
  )
}

function SimplifyPanel({ language, setLanguage }) {
  const [text, setText] = useDraft('simplify', '')
  const [state, run] = useAiCall(aiApi.simplify, 'simplify')
  const r = state.data
  return (
    <div className="space-y-5">
      <form className="card space-y-4" onSubmit={(e) => { e.preventDefault(); run({ text, language }) }}>
        <LanguageSelect label="Explain in" value={language} onChange={setLanguage} />
        <TextInput value={text} onChange={setText} placeholder="e.g. Diagnosed with Type 2 DM with HTN. Advised HbA1c every 3 months." />
        <SubmitRow busy={state.busy} disabled={text.trim().length < 2} label="Explain simply" />
      </form>
      <Alert type="error">{state.error}</Alert>
      {state.busy && <Spinner label="Preparing a simple explanation…" />}
      {r && (
        <>
          <ResultActions language={r._language || language} text={[r.simple_explanation, ...r.key_points, ...r.guidance].join(NL)} />
          <Section icon={Lightbulb} title="What this means"><p className="whitespace-pre-line text-lg leading-relaxed">{r.simple_explanation}</p></Section>
          <Section icon={ListChecks} title="Key points"><BulletList items={r.key_points} /></Section>
          <Section icon={ShieldCheck} title="What you can do"><BulletList items={r.guidance} /></Section>
          <Section icon={MessageCircleQuestion} title="Questions to ask your doctor"><BulletList items={r.questions_for_doctor} /></Section>
          <Glossary terms={r.glossary} />
          <AiDisclaimer />
        </>
      )}
    </div>
  )
}

function ExtractPanel({ language, setLanguage }) {
  const [text, setText] = useDraft('extract', '')
  const [state, run] = useAiCall(aiApi.extract, 'extract')
  const r = state.data
  return (
    <div className="space-y-5">
      <form className="card space-y-4" onSubmit={(e) => { e.preventDefault(); run({ text, language }) }}>
        <LanguageSelect label="Explanations in" value={language} onChange={setLanguage} />
        <TextInput value={text} onChange={setText} placeholder={SAMPLE} />
        <SubmitRow busy={state.busy} disabled={text.trim().length < 2} label="Find medical information" onSample={() => setText(SAMPLE)} />
      </form>
      <Alert type="error">{state.error}</Alert>
      {state.busy && <Spinner label="Reading the text…" />}
      {r && (
        <>
          {r.summary && <Alert type="info">{r.summary}</Alert>}
          <EntitiesView entities={r.entities} />
          <AiDisclaimer />
        </>
      )}
    </div>
  )
}

function SymptomPanel({ language, setLanguage }) {
  const [form, setForm] = useDraft('symptoms', { symptoms: '', age: '', gender: '', duration: '' })
  const [state, run] = useAiCall(aiApi.symptoms, 'symptoms')
  const r = state.data
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const submit = (e) => {
    e.preventDefault()
    run({
      symptoms: form.symptoms.trim(), language,
      age: form.age === '' ? null : Number(form.age), gender: form.gender || null, duration: form.duration.trim() || null,
    })
  }
  return (
    <div className="space-y-5">
      <Alert type="warning">
        If someone has chest pain, trouble breathing, fainting, fits, heavy bleeding or sudden weakness, do not wait: call 108 now.
      </Alert>
      <form className="card space-y-4" onSubmit={submit}>
        <Field label="Describe the symptoms">
          <textarea className="input min-h-28" value={form.symptoms} onChange={set('symptoms')} maxLength={2000}
            placeholder="e.g. Fever with body pain and headache since 3 days, no appetite" />
        </Field>
        <div className="grid gap-4 sm:grid-cols-4">
          <Field label="Age (optional)"><input className="input" type="number" min="0" max="120" value={form.age} onChange={set('age')} /></Field>
          <Field label="Gender (optional)">
            <select className="input" value={form.gender} onChange={set('gender')}>
              <option value="">—</option><option>Female</option><option>Male</option><option>Other</option>
            </select>
          </Field>
          <Field label="For how long"><input className="input" value={form.duration} onChange={set('duration')} placeholder="3 days" /></Field>
          <LanguageSelect label="Answer in" value={language} onChange={setLanguage} />
        </div>
        <SubmitRow busy={state.busy} disabled={form.symptoms.trim().length < 3} label="Get guidance" />
      </form>
      <Alert type="error">{state.error}</Alert>
      {state.busy && <Spinner label="Looking at the symptoms…" />}
      {r && (
        <>
          <UrgencyBanner urgency={r.urgency} reason={r.urgency_reason} />
          <ResultActions language={r._language || language} text={[r.summary, ...r.self_care, ...r.see_doctor_if].join(NL)} />
          <Section icon={Sparkles} title="Summary"><p className="leading-relaxed">{r.summary}</p></Section>
          <WarningSigns items={r.emergency_signs} title="Go to hospital at once if" />
          {r.possible_causes.length > 0 && (
            <Section icon={Stethoscope} title="Possible causes to discuss with a doctor">
              <ul className="space-y-2">{r.possible_causes.map((c, i) => (
                <li key={i}><span className="font-semibold">{c.name}</span><span className="text-slate-600"> — {c.explanation}</span></li>
              ))}</ul>
            </Section>
          )}
          <Section icon={HeartPulse} title="Care at home"><BulletList items={r.self_care} /></Section>
          <Section icon={Stethoscope} title="See a doctor if"><BulletList items={r.see_doctor_if} /></Section>
          <Section icon={ShieldCheck} title="Prevention"><BulletList items={r.prevention} /></Section>
          <RelatedContent items={r.related_content} />
          <Alert type="info">{r.disclaimer}</Alert>
        </>
      )}
    </div>
  )
}

function SubmitRow({ busy, disabled, label, onSample }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button className="btn-primary" disabled={busy || disabled}><Sparkles className="h-4 w-4" />{busy ? 'Working…' : label}</button>
      {onSample && <button type="button" className="btn-ghost text-sm" onClick={onSample}>Use an example</button>}
    </div>
  )
}

export default function Assistant() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const tab = TABS.some(([k]) => k === params.get('tab')) ? params.get('tab') : 'translate'
  const [language, setLanguage] = useState(user.preferred_language || 'en')
  const [status, setStatus] = useState(null)
  useEffect(() => { aiApi.status().then(({ data }) => setStatus(data)).catch(() => {}) }, [])

  const Panel = { translate: TranslatePanel, simplify: SimplifyPanel, extract: ExtractPanel, symptoms: SymptomPanel }[tab]
  return (
    <div className="space-y-6">
      <PageHeader title="AI Health Assistant"
        subtitle="Translate prescriptions and instructions, understand medical words, and learn about symptoms in your language." />
      <AiStatusNotice status={status} />
      <div className="flex flex-wrap gap-1 rounded-2xl bg-slate-100 p-1">
        {TABS.map(([key, label, Icon]) => (
          <button key={key} onClick={() => setParams({ tab: key })}
            className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${tab === key ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
            <Icon className="h-4 w-4" /><span>{label}</span>
          </button>
        ))}
      </div>
      <Panel key={tab} language={language} setLanguage={setLanguage} />
    </div>
  )
}
