import { ArrowLeft, Eye, FileImage, FileText, Languages, RefreshCw, ScanText, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  AiDisclaimer, AiStatusNotice, EntitiesView, Glossary, LanguageSelect, ResultActions, SavedTranslations, Section,
  WarningSigns,
} from '../components/ai'
import { Alert, PageHeader, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { aiApi, documentApi, errorMessage } from '../services/api'
import { LANGUAGES, formatDateTime, labelFor, languageLabel } from '../utils/constants'

const POLL_MS = 3000

/** The uploaded prescription itself, shown beside the translation and included when printing. */
function OriginalDocument({ doc }) {
  const [url, setUrl] = useState(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let objectUrl = null
    let cancelled = false
    documentApi.objectUrl(doc)
      .then((u) => { objectUrl = u; if (cancelled) URL.revokeObjectURL(u); else setUrl(u) })
      .catch(() => setFailed(true))
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [doc])

  const isPdf = doc.mime_type === 'application/pdf'
  return (
    <section className="card space-y-3 lg:sticky lg:top-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <FileImage className="h-5 w-5 text-brand-700" />Your original {labelFor(doc.document_type).toLowerCase()}
        </h2>
        {url && (
          <a href={url} target="_blank" rel="noreferrer" className="no-print btn-ghost px-2 py-1 text-sm">
            <Eye className="h-4 w-4" />Full size
          </a>
        )}
      </div>
      <p className="text-xs text-slate-500">{doc.document_name}{doc.document_date ? ` · ${doc.document_date}` : ''}</p>
      {failed ? <Alert type="warning">The original file could not be loaded.</Alert> : !url ? <Spinner /> : isPdf ? (
        <>
          <iframe src={url} title={doc.document_name} className="no-print h-[32rem] w-full rounded-xl border border-slate-200" />
          <p className="hidden text-sm text-slate-600 print:block">The original is a PDF file: print it separately from the Documents page.</p>
        </>
      ) : (
        <img src={url} alt={`Original ${labelFor(doc.document_type).toLowerCase()}: ${doc.document_name}`}
          className="mx-auto max-h-[36rem] w-full rounded-xl border border-slate-200 bg-slate-50 object-contain print:max-h-[55vh] print:border-0" />
      )}
    </section>
  )
}

export default function DocumentInsight() {
  const { documentId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  // The language lives in the URL (?lang=te) so Back, refresh and bookmarks reopen the same translation.
  const [params, setParams] = useSearchParams()
  const urlLang = LANGUAGES.some((l) => l.code === params.get('lang')) ? params.get('lang') : null
  const language = urlLang || user.preferred_language || 'en'
  const setLanguage = useCallback((code) => setParams({ lang: code }, { replace: true }), [setParams])
  const [saved, setSaved] = useState(null)
  const [doc, setDoc] = useState(null)
  const [status, setStatus] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showOriginal, setShowOriginal] = useState(false)
  const timer = useRef(null)

  useEffect(() => {
    documentApi.get(documentId).then(({ data }) => setDoc(data)).catch((err) => setError(errorMessage(err)))
    aiApi.status().then(({ data }) => setStatus(data)).catch(() => {})
  }, [documentId])

  const loadSaved = useCallback(() => aiApi.documentAnalyses(documentId)
    .then(({ data }) => { setSaved(data); return data })
    .catch(() => { setSaved([]); return [] }), [documentId])

  // No language in the URL: open the most recent saved translation, if there is one.
  useEffect(() => {
    loadSaved().then((items) => {
      const latest = items.find((a) => a.status === 'COMPLETED')
      if (!urlLang && latest) setLanguage(latest.language_code)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadSaved])

  const load = useCallback(async () => {
    clearTimeout(timer.current)
    try {
      const { data } = await aiApi.documentAnalysis(documentId, language)
      setAnalysis(data)
      if (data.status === 'PENDING' || data.status === 'PROCESSING') timer.current = setTimeout(load, POLL_MS)
      else if (data.status === 'COMPLETED') loadSaved()
    } catch (err) {
      if (err.response?.status === 404) setAnalysis(null)
      else setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [documentId, language, loadSaved])

  useEffect(() => {
    setLoading(true); setError(''); setAnalysis(null)
    load()
    return () => clearTimeout(timer.current)
  }, [load])

  const start = async (force = false) => {
    setError('')
    try {
      const { data } = await aiApi.analyzeDocument(documentId, language, force)
      setAnalysis(data)
      timer.current = setTimeout(load, POLL_MS)
    } catch (err) {
      setError(errorMessage(err, 'Could not start the analysis.'))
    }
  }

  const busy = analysis && (analysis.status === 'PENDING' || analysis.status === 'PROCESSING')
  const result = analysis?.status === 'COMPLETED' ? analysis.result : null

  return (
    <div className="space-y-6">
      <button className="btn-ghost no-print -ml-3" onClick={() => navigate(-1)}><ArrowLeft className="h-4 w-4" />Back</button>
      <PageHeader title="Understand your document"
        subtitle={doc ? `${doc.document_name} · ${labelFor(doc.document_type)}` : 'AI explanation and translation'} />
      <AiStatusNotice status={status} />

      <div className="card no-print flex flex-wrap items-end gap-4">
        <LanguageSelect className="min-w-56 flex-1" label="Explain in" value={language} onChange={setLanguage} />
        {!busy && (!analysis || analysis.status === 'FAILED') && (
          <button className="btn-primary" onClick={() => start(analysis?.status === 'FAILED')} disabled={status && !status.enabled}>
            <Sparkles className="h-4 w-4" />{analysis?.status === 'FAILED' ? 'Try again' : 'Explain this document'}
          </button>
        )}
        {result && (
          <button className="btn-secondary" onClick={() => start(true)}><RefreshCw className="h-4 w-4" />Re-read document</button>
        )}
      </div>

      <SavedTranslations items={saved} current={language} onSelect={setLanguage} />
      <Alert type="error">{error}</Alert>
      {loading ? <Spinner /> : busy ? (
        <div className="card text-center">
          <Spinner label="Reading the document and preparing a simple explanation…" className="py-6" />
          <p className="text-sm text-slate-500">This usually takes under a minute. You can leave this page and come back.</p>
        </div>
      ) : analysis?.status === 'FAILED' ? (
        <Alert type="error">The analysis did not finish: {analysis.error}</Alert>
      ) : !analysis ? (
        <div className="card text-center text-slate-600">
          <ScanText className="mx-auto h-10 w-10 text-brand-600" />
          <p className="mt-3">Get this document explained in {languageLabel(language)}: the medicines, what they are for, what to do next,
            and a full translation in simple words.</p>
        </div>
      ) : result && !result.is_medical_document ? (
        <Alert type="warning">This file does not look like a medical document, so there is nothing to explain.</Alert>
      ) : result && (
        <>
          <ResultActions language={analysis.language_code}
            text={`${result.summary}

${result.translation}`} />
          {result.readability !== 'clear' && (
            <Alert type="warning">
              Parts of this document were hard to read{result.unclear_parts.length ? `: ${result.unclear_parts.join('; ')}` : '.'} Please
              confirm these with your doctor or pharmacist.
            </Alert>
          )}
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          {doc && <OriginalDocument doc={doc} />}
          <div className="min-w-0 space-y-6">
          <Section icon={Sparkles} title="In simple words">
            <p className="whitespace-pre-line text-lg leading-relaxed text-slate-800">{result.summary}</p>
          </Section>
          <WarningSigns items={result.warning_signs} />
          <EntitiesView entities={result.entities} />
          <Section icon={Languages} title={`Full translation — ${languageLabel(analysis.language_code)}`}>
            <p className="whitespace-pre-line leading-relaxed text-slate-800">{result.translation}</p>
          </Section>
          <Glossary terms={result.glossary} />
          <section className="card">
            <button className="flex w-full items-center justify-between text-left font-semibold" onClick={() => setShowOriginal((v) => !v)}>
              <span className="flex items-center gap-2"><FileText className="h-5 w-5 text-slate-500" />Text found in the document ({result.source_language})</span>
              <span className="text-sm text-brand-700">{showOriginal ? 'Hide' : 'Show'}</span>
            </button>
            {showOriginal && <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-slate-50 p-4 font-sans text-sm text-slate-700">{result.extracted_text}</pre>}
          </section>
          <p className="text-xs text-slate-400">Prepared {formatDateTime(analysis.completed_at)}</p>
          <AiDisclaimer />
          </div>
          </div>
        </>
      )}
    </div>
  )
}
