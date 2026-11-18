import { RefreshCw, ShieldCheck } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { authApi, errorMessage } from '../services/api'
import { Alert, Field } from './ui'

const RESEND_SECONDS = 60

/**
 * Enter the SMS code for `identifier` (phone or email of the account).
 * A code is assumed to have just been sent (registration, login and phone changes send one automatically).
 */
export default function OtpVerify({ identifier, onVerified, compact = false }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(RESEND_SECONDS)
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])
  useEffect(() => {
    if (cooldown <= 0) return undefined
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const submit = async (e) => {
    e.preventDefault()
    if (!/^[0-9]{6}$/.test(code)) { setError('Enter the 6-digit code from the SMS.'); return }
    setBusy(true); setError(''); setInfo('')
    try {
      await authApi.verifyPhone(identifier, code)
      onVerified?.()
    } catch (err) {
      setError(errorMessage(err, 'Verification failed.'))
      setCode('')
      inputRef.current?.focus()
    } finally {
      setBusy(false)
    }
  }

  const resend = async () => {
    setError(''); setInfo('')
    try {
      const { data } = await authApi.sendOtp(identifier)
      setInfo('A new code has been sent.')
      setCooldown(data.resend_after ?? RESEND_SECONDS)
    } catch (err) {
      const retry = Number(err.response?.headers?.['retry-after'])
      if (retry > 0) setCooldown(retry)
      setError(errorMessage(err, 'Could not resend the code.'))
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <Field label="Verification code" hint="Sent by SMS · valid for 5 minutes">
        <input ref={inputRef} className={`input tracking-[0.5em] text-center font-mono ${compact ? 'text-lg' : 'text-2xl'}`}
          inputMode="numeric" autoComplete="one-time-code" maxLength={6} placeholder="••••••"
          value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
      </Field>
      <Alert type="error">{error}</Alert>
      <Alert type="success">{info}</Alert>
      <div className={`flex gap-3 ${compact ? 'flex-wrap' : 'flex-col'}`}>
        <button className={`btn-primary ${compact ? '' : 'w-full'}`} disabled={busy || code.length !== 6}>
          <ShieldCheck className="h-4 w-4" />{busy ? 'Verifying…' : 'Verify phone number'}
        </button>
        <button type="button" onClick={resend} disabled={cooldown > 0}
          className="inline-flex items-center justify-center gap-2 text-sm font-semibold text-brand-700 hover:underline disabled:cursor-not-allowed disabled:text-slate-400 disabled:no-underline">
          <RefreshCw className="h-4 w-4" />{cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
        </button>
      </div>
    </form>
  )
}
