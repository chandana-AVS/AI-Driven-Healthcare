import { Plus } from 'lucide-react'
import { useState } from 'react'
import { errorMessage } from '../services/api'
import { RECORD_TYPES, labelFor, today } from '../utils/constants'
import { Alert, Field } from './ui'

export default function RecordForm({ onSubmit, documents = [] }) {
  const empty = { record_type: 'CONSULTATION', title: '', description: '', record_date: today(), document_id: '' }
  const [form, setForm] = useState(empty)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (form.title.trim().length < 2) return setError('Please enter a title.')
    setBusy(true); setError('')
    try {
      await onSubmit({ ...form, title: form.title.trim(), description: form.description.trim() || null, document_id: form.document_id || null })
      setForm(empty)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-4">
      <h2 className="text-lg font-semibold">Add healthcare record</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Record type">
          <select className="input" value={form.record_type} onChange={set('record_type')}>
            {RECORD_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </Field>
        <Field label="Date">
          <input type="date" className="input" max={today()} value={form.record_date} onChange={set('record_date')} required />
        </Field>
      </div>
      <Field label="Title">
        <input className="input" value={form.title} onChange={set('title')} maxLength={255} placeholder="e.g. Blood pressure check" required />
      </Field>
      <Field label="Notes">
        <textarea className="input min-h-24" value={form.description} onChange={set('description')} maxLength={10000} />
      </Field>
      {documents.length > 0 && (
        <Field label="Link a document (optional)">
          <select className="input" value={form.document_id} onChange={set('document_id')}>
            <option value="">— None —</option>
            {documents.map((d) => <option key={d.id} value={d.id}>{d.document_name} ({labelFor(d.document_type)})</option>)}
          </select>
        </Field>
      )}
      <Alert type="error">{error}</Alert>
      <button className="btn-primary" disabled={busy}><Plus className="h-4 w-4" />{busy ? 'Saving…' : 'Save record'}</button>
    </form>
  )
}
