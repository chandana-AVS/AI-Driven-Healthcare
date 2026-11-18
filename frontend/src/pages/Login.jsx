import { Eye, EyeOff, LogIn } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Alert, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../services/api'
import { ROLE_HOME } from '../utils/constants'

const PHONE_NOT_VERIFIED = 'Phone number not verified'

export default function Login() {
  const { user, login, sessionMessage } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState(location.state?.identifier || '')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (identifier.trim().length < 3) errs.identifier = 'Enter your email address or phone number.'
    if (!password) errs.password = 'Enter your password.'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true); setError('')
    try {
      const me = await login(identifier.trim(), password)
      const from = location.state?.from
      navigate(from && from !== '/login' ? from : ROLE_HOME[me.role], { replace: true })
    } catch (err) {
      if (err.response?.status === 403 && err.response.data?.detail === PHONE_NOT_VERIFIED) {
        // The backend has just sent a fresh code.
        navigate('/verify-phone', { state: { identifier: identifier.trim(), fromLogin: true } })
        return
      }
      setError(errorMessage(err, 'Login failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="card p-7">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-500">Log in with your email address or phone number.</p>
        {location.state?.registered && <Alert type="success" className="mt-4">Account created! Please log in.</Alert>}
        {location.state?.verified && <Alert type="success" className="mt-4">Phone number verified! Your account is ready — please log in.</Alert>}
        {sessionMessage && <Alert type="warning" className="mt-4">{sessionMessage}</Alert>}
        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <Field label="Email or phone number" error={errors.identifier}>
            <input className="input" autoComplete="username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="you@example.com or 9876543210" />
          </Field>
          <Field label="Password" error={errors.password}>
            <div className="relative">
              <input className="input pr-10" type={show ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" className="absolute inset-y-0 right-0 px-3 text-slate-400 hover:text-slate-600" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </Field>
          <Alert type="error">{error}</Alert>
          <button className="btn-primary w-full" disabled={busy}><LogIn className="h-4 w-4" />{busy ? 'Logging in…' : 'Login'}</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">
          New here? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create an account</Link>
        </p>
      </div>
    </div>
  )
}
