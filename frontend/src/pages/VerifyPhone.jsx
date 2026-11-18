import { Smartphone } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import OtpVerify from '../components/OtpVerify'
import { Alert } from '../components/ui'

/** Shows the last 4 digits only, e.g. "••••••3210". Emails are not shown. */
function maskPhone(value) {
  const digits = (value || '').replace(/\D/g, '')
  return digits.length >= 4 ? `••••••${digits.slice(-4)}` : null
}

export default function VerifyPhone() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const identifier = state?.identifier
  if (!identifier) return <Navigate to="/login" replace />

  const masked = maskPhone(state.phone || (identifier.includes('@') ? '' : identifier))

  return (
    <div className="mx-auto max-w-md">
      <div className="card p-7">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
          <Smartphone className="h-7 w-7" />
        </div>
        <h1 className="mt-4 text-center text-2xl font-bold">Verify your phone number</h1>
        <p className="mt-1 text-center text-sm text-slate-500">
          We sent a 6-digit code by SMS to {masked ? <span className="font-semibold text-slate-700">{masked}</span> : 'the phone number on your account'}.
        </p>
        {import.meta.env.VITE_OTP_HINT && (
          <Alert type="info" className="mt-4">
            Test mode: SMS is not connected yet. Use code <span className="font-mono font-bold">{import.meta.env.VITE_OTP_HINT}</span>.
          </Alert>
        )}
        {state.fromLogin && (
          <Alert type="warning" className="mt-4">Your phone number isn't verified yet. Enter the code to continue.</Alert>
        )}
        <div className="mt-6">
          <OtpVerify identifier={identifier}
            onVerified={() => navigate('/login', { replace: true, state: { verified: true, identifier } })} />
        </div>
        <p className="mt-6 text-center text-sm text-slate-500">
          <Link to="/login" className="font-semibold text-brand-700 hover:underline">Back to login</Link>
        </p>
      </div>
    </div>
  )
}
