import { ShieldCheck, Stethoscope, User } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import LanguageSelector from '../components/LanguageSelector'
import { Alert, Field } from '../components/ui'
import { authApi, errorMessage } from '../services/api'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PHONE_RE = /^\+?[0-9]{7,15}$/

const ROLES = {
  patient: { label: 'Patient', icon: User, register: authApi.registerPatient },
  worker: { label: 'Healthcare Worker', icon: Stethoscope, register: authApi.registerWorker },
  admin: { label: 'Admin', icon: ShieldCheck, register: authApi.registerAdmin },
}

function validate(form, role) {
  const e = {}
  if (form.full_name.trim().length < 2) e.full_name = 'Please enter your full name.'
  const email = form.email.trim()
  const phone = form.phone.replace(/[\s\-()]/g, '')
  if (!phone) e.phone = 'Phone number is required — we will send you a verification code.'
  else if (!PHONE_RE.test(phone)) e.phone = 'Enter a valid phone number (7–15 digits).'
  if (email && !EMAIL_RE.test(email)) e.email = 'Enter a valid email address.'
  if (form.password.length < 8) e.password = 'Use at least 8 characters.'
  else if (!/[A-Za-z]/.test(form.password) || !/[0-9]/.test(form.password)) e.password = 'Include at least one letter and one number.'
  if (form.confirm !== form.password) e.confirm = 'Passwords do not match.'
  if (role === 'worker') {
    if (form.designation.trim().length < 2) e.designation = 'Enter your designation.'
    if (form.organization.trim().length < 2) e.organization = 'Enter your organization.'
  }
  if (role === 'admin') {
    if (form.employee_id.trim().length < 2) e.employee_id = 'Enter your employee ID.'
    if (form.hospital_name.trim().length < 2) e.hospital_name = 'Enter your hospital name.'
  }
  return e
}

export default function Register() {
  const [params, setParams] = useSearchParams()
  const role = ROLES[params.get('role')] ? params.get('role') : 'patient'
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '', confirm: '', designation: '', organization: '',
    employee_id: '', hospital_name: '', preferred_language: 'en',
  })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    const errs = validate(form, role)
    setErrors(errs)
    if (Object.keys(errs).length) return
    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim(),
      password: form.password,
      preferred_language: form.preferred_language,
      ...(role === 'worker' && { designation: form.designation.trim(), organization: form.organization.trim() }),
      ...(role === 'admin' && { employee_id: form.employee_id.trim(), hospital_name: form.hospital_name.trim() }),
    }
    setBusy(true); setError('')
    try {
      await ROLES[role].register(payload)
      navigate('/verify-phone', { state: { identifier: payload.phone, phone: payload.phone } })
    } catch (err) {
      setError(errorMessage(err, 'Registration failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="card p-7">
        <h1 className="text-2xl font-bold">Create your account</h1>
        <div className="mt-5 flex gap-1 rounded-2xl bg-slate-100 p-1">
          {Object.entries(ROLES).map(([key, { label, icon: Icon }]) => (
            <button key={key} type="button" onClick={() => { setParams(key === 'patient' ? {} : { role: key }); setErrors({}); setError('') }}
              className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${role === key ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
              <Icon className="h-4 w-4" /><span className="hidden sm:inline">{label}</span><span className="sm:hidden">{label.split(' ')[0]}</span>
            </button>
          ))}
        </div>
        {role === 'worker' && (
          <Alert type="info" className="mt-4">
            Healthcare-worker accounts are reviewed by an administrator. You can log in straight away, but you
            can only see patient records after verification and when a patient grants you access.
          </Alert>
        )}
        {role === 'admin' && (
          <Alert type="warning" className="mt-4">
            Administrator accounts must be approved by an existing administrator, who will verify your employee ID
            with your hospital. Until then you can log in, but you will not have any admin permissions.
          </Alert>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <Field label="Full name" error={errors.full_name}>
            <input className="input" autoComplete="name" value={form.full_name} onChange={set('full_name')} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Phone number *" error={errors.phone} hint="We'll send a verification code by SMS">
              <input className="input" type="tel" autoComplete="tel" value={form.phone} onChange={set('phone')} placeholder="9876543210" />
            </Field>
            <Field label="Email (optional)" error={errors.email}>
              <input className="input" type="email" autoComplete="email" value={form.email} onChange={set('email')} />
            </Field>
          </div>
          {role === 'worker' && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Designation" error={errors.designation}>
                <input className="input" value={form.designation} onChange={set('designation')} placeholder="Nurse, ASHA worker, Doctor…" />
              </Field>
              <Field label="Organization" error={errors.organization}>
                <input className="input" value={form.organization} onChange={set('organization')} placeholder="Primary Health Centre" />
              </Field>
            </div>
          )}
          {role === 'admin' && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Employee ID" error={errors.employee_id}>
                <input className="input" value={form.employee_id} onChange={set('employee_id')} maxLength={50} placeholder="e.g. EMP1024" />
              </Field>
              <Field label="Hospital name" error={errors.hospital_name}>
                <input className="input" value={form.hospital_name} onChange={set('hospital_name')} maxLength={150} placeholder="District Hospital" />
              </Field>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Password" error={errors.password} hint="At least 8 characters, with a letter and a number">
              <input className="input" type="password" autoComplete="new-password" value={form.password} onChange={set('password')} />
            </Field>
            <Field label="Confirm password" error={errors.confirm}>
              <input className="input" type="password" autoComplete="new-password" value={form.confirm} onChange={set('confirm')} />
            </Field>
          </div>
          <Field label="Preferred language">
            <LanguageSelector value={form.preferred_language} onChange={(v) => setForm((f) => ({ ...f, preferred_language: v }))} />
          </Field>
          <Alert type="error">{error}</Alert>
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Creating account…' : `Register as ${ROLES[role].label}`}</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Login</Link>
        </p>
      </div>
    </div>
  )
}
