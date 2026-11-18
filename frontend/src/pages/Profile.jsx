import { Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import LanguageSelector from '../components/LanguageSelector'
import OtpVerify from '../components/OtpVerify'
import { Alert, Field, PageHeader, Spinner, StatusBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { errorMessage, patientApi, userApi, workerApi } from '../services/api'
import { languageLabel, today } from '../utils/constants'

function useMessage() {
  const [msg, setMsg] = useState({ type: '', text: '' })
  return [msg, (type, text) => setMsg({ type, text })]
}

export default function Profile() {
  const { user, setUser } = useAuth()
  const isPatient = user.role === 'PATIENT'
  const isWorker = user.role === 'HEALTHCARE_WORKER'

  const [account, setAccount] = useState({ full_name: user.full_name, email: user.email || '', phone: user.phone || '' })
  const [accountMsg, setAccountMsg] = useMessage()
  const [langMsg, setLangMsg] = useMessage()
  const [extra, setExtra] = useState(null)
  const [extraMsg, setExtraMsg] = useMessage()
  const [busy, setBusy] = useState('')

  useEffect(() => {
    if (isPatient) patientApi.me().then(({ data }) => setExtra({
      date_of_birth: data.profile.date_of_birth || '', gender: data.profile.gender || '', address: data.profile.address || '',
      emergency_contact_name: data.profile.emergency_contact_name || '', emergency_contact_phone: data.profile.emergency_contact_phone || '',
    }))
    else if (isWorker) workerApi.me().then(({ data }) => setExtra({
      designation: data.profile.designation || '', organization: data.profile.organization || '', verification_status: data.profile.verification_status,
    }))
  }, [isPatient, isWorker])

  const run = async (key, fn, setMsg, ok) => {
    setBusy(key); setMsg('', '')
    try { await fn(); setMsg('success', ok) } catch (err) { setMsg('error', errorMessage(err)) } finally { setBusy('') }
  }

  const saveAccount = (e) => {
    e.preventDefault()
    run('account', async () => {
      const { data } = await userApi.update({
        full_name: account.full_name.trim(), email: account.email.trim() || null, phone: account.phone.trim() || null,
      })
      setUser(data)
    }, setAccountMsg, account.phone.trim() && account.phone.trim() !== user.phone
      ? 'Saved. We sent a verification code to your new phone number.' : 'Personal information updated.')
  }

  const changeLanguage = (code) => run('lang', async () => {
    const { data } = await userApi.updateLanguage(code)
    setUser(data)
  }, setLangMsg, `Preferred language set to ${languageLabel(code)}.`)

  const saveExtra = (e) => {
    e.preventDefault()
    run('extra', async () => {
      if (isPatient) {
        const payload = Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, v.trim?.() || null]))
        await patientApi.updateProfile(payload)
      } else {
        await workerApi.update({ designation: extra.designation.trim() || null, organization: extra.organization.trim() || null })
      }
    }, setExtraMsg, 'Profile details saved.')
  }

  const setA = (k) => (e) => setAccount((a) => ({ ...a, [k]: e.target.value }))
  const setE = (k) => (e) => setExtra((x) => ({ ...x, [k]: e.target.value }))

  return (
    <div className="space-y-6">
      <PageHeader title="My Profile" subtitle="Manage your personal information, contact details and language." />

      <form onSubmit={saveAccount} className="card space-y-4">
        <h2 className="text-lg font-semibold">Personal information</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Full name"><input className="input" value={account.full_name} onChange={setA('full_name')} required minLength={2} /></Field>
          <Field label="Email"><input className="input" type="email" value={account.email} onChange={setA('email')} /></Field>
          <Field label="Phone *"><input className="input" type="tel" value={account.phone} onChange={setA('phone')} required /></Field>
        </div>
        <Alert type={accountMsg.type}>{accountMsg.text}</Alert>
        <button className="btn-primary" disabled={busy === 'account'}><Save className="h-4 w-4" />Save changes</button>
      </form>

      {user.phone && !user.phone_verified && (
        <section className="card space-y-4 border-amber-200">
          <div>
            <h2 className="text-lg font-semibold">Verify your phone number</h2>
            <p className="text-sm text-slate-500">
              Enter the code we sent to {user.phone}. You will need a verified number the next time you log in.
            </p>
          </div>
          <OtpVerify compact identifier={user.phone} onVerified={async () => {
            const { data } = await userApi.me()
            setUser(data)
            setAccountMsg('success', 'Phone number verified.')
          }} />
        </section>
      )}

      <section className="card space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Preferred language</h2>
          <p className="text-sm text-slate-500">Health information and future translations will use this language.</p>
        </div>
        <LanguageSelector value={user.preferred_language} onChange={changeLanguage} disabled={busy === 'lang'} />
        <Alert type={langMsg.type}>{langMsg.text}</Alert>
      </section>

      {(isPatient || isWorker) && (
        <form onSubmit={saveExtra} className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{isPatient ? 'Health profile' : 'Professional profile'}</h2>
            {isWorker && extra && <StatusBadge status={extra.verification_status} />}
          </div>
          {!extra ? <Spinner /> : isPatient ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Date of birth"><input type="date" className="input" max={today()} value={extra.date_of_birth} onChange={setE('date_of_birth')} /></Field>
                <Field label="Gender">
                  <select className="input" value={extra.gender} onChange={setE('gender')}>
                    <option value="">Prefer not to say</option><option>Female</option><option>Male</option><option>Other</option>
                  </select>
                </Field>
              </div>
              <Field label="Address"><textarea className="input" rows={2} value={extra.address} onChange={setE('address')} /></Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Emergency contact name"><input className="input" value={extra.emergency_contact_name} onChange={setE('emergency_contact_name')} /></Field>
                <Field label="Emergency contact phone"><input className="input" type="tel" value={extra.emergency_contact_phone} onChange={setE('emergency_contact_phone')} /></Field>
              </div>
            </>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Designation"><input className="input" value={extra.designation} onChange={setE('designation')} /></Field>
              <Field label="Organization"><input className="input" value={extra.organization} onChange={setE('organization')} /></Field>
            </div>
          )}
          <Alert type={extraMsg.type}>{extraMsg.text}</Alert>
          <button className="btn-primary" disabled={busy === 'extra' || !extra}><Save className="h-4 w-4" />Save profile</button>
        </form>
      )}
    </div>
  )
}
