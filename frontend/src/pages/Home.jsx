import { FileHeart, History, Languages, Lock, Stethoscope, UserPlus, Users } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LANGUAGES, ROLE_HOME } from '../utils/constants'

const FEATURES = [
  { icon: FileHeart, title: 'Keep medical documents safe', text: 'Upload prescriptions, discharge summaries, diagnostic and lab reports. Files are stored privately.' },
  { icon: History, title: 'Your health history in one place', text: 'See documents and healthcare records in date order, ready for every visit.' },
  { icon: Users, title: 'You control who sees your records', text: 'Give access to a verified healthcare worker and take it back at any time.' },
  { icon: Languages, title: 'Choose your language', text: 'Set your preferred language now — later updates will explain medical information in it.' },
  { icon: Lock, title: 'Secure by design', text: 'Encrypted passwords, signed login tokens, role-based access and an audit trail.' },
  { icon: Stethoscope, title: 'Built for health workers', text: 'ASHA workers, nurses and doctors can view and manage records of patients who authorised them.' },
]

export default function Home() {
  const { user } = useAuth()
  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />

  return (
    <div className="space-y-14">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-800 via-brand-700 to-brand-600 px-6 py-14 text-white sm:px-12">
        <div className="max-w-2xl">
          <p className="mb-3 inline-block rounded-full bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-wider">
            AI-Driven Healthcare Assistance for Rural Communities
          </p>
          <h1 className="text-3xl font-bold leading-tight text-white sm:text-5xl">
            Understand your health information — in your own language.
          </h1>
          <p className="mt-4 text-lg text-brand-50">
            A simple, secure place for patients and healthcare workers to store and share medical documents,
            prescriptions and health history.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register?role=patient" className="btn bg-white text-brand-800 hover:bg-brand-50"><UserPlus className="h-4 w-4" />Register as Patient</Link>
            <Link to="/register?role=worker" className="btn border border-white/40 text-white hover:bg-white/10"><Stethoscope className="h-4 w-4" />Register as Healthcare Worker</Link>
            <Link to="/login" className="btn text-white underline-offset-4 hover:underline">Already registered? Login</Link>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-6 text-2xl font-bold">What you can do</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="card">
              <Icon className="mb-3 h-8 w-8 text-brand-600" />
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-slate-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 className="text-xl font-bold">Languages supported</h2>
        <p className="mt-1 text-sm text-slate-600">Pick your preferred language when you register. You can change it any time from your profile.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {LANGUAGES.map((l) => (
            <span key={l.code} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2">
              <span className="text-lg font-semibold">{l.native}</span>
              <span className="ml-2 text-sm text-slate-500">{l.name}</span>
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}
