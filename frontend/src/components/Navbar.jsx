import { HeartPulse, LogOut, Menu, UserCircle, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ROLE_HOME } from '../utils/constants'

const LINKS = {
  PATIENT: [
    ['/patient', 'Dashboard'], ['/documents', 'Documents'], ['/history', 'Medical History'],
    ['/care-team', 'Care Team'], ['/assistant', 'AI Assistant'], ['/health-info', 'Health Info'],
  ],
  HEALTHCARE_WORKER: [['/worker', 'Dashboard'], ['/assistant', 'AI Assistant'], ['/health-info', 'Health Info']],
  ADMIN: [['/admin', 'Admin Dashboard'], ['/health-info', 'Health Info']],
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const links = user ? LINKS[user.role] || [] : [['/health-info', 'Health Info']]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const linkClass = ({ isActive }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to={user ? ROLE_HOME[user.role] : '/'} className="flex items-center gap-2 font-bold text-brand-800">
          <HeartPulse className="h-7 w-7 text-brand-600" />
          <span className="text-lg">Rural Health Assistant</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map(([to, label]) => <NavLink key={to} to={to} className={linkClass}>{label}</NavLink>)}
          {user ? (
            <>
              <NavLink to="/profile" className={linkClass}>
                <span className="flex items-center gap-1.5"><UserCircle className="h-4 w-4" />{user.full_name.split(' ')[0]}</span>
              </NavLink>
              <button onClick={handleLogout} className="btn-ghost"><LogOut className="h-4 w-4" />Logout</button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={linkClass}>Login</NavLink>
              <Link to="/register" className="btn-primary ml-2">Register</Link>
            </>
          )}
        </nav>

        <button className="btn-ghost md:hidden" onClick={() => setOpen((v) => !v)} aria-label="Toggle menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <nav className="flex flex-col gap-1 border-t border-slate-200 bg-white px-4 py-3 md:hidden" onClick={() => setOpen(false)}>
          {links.map(([to, label]) => <NavLink key={to} to={to} className={linkClass}>{label}</NavLink>)}
          {user ? (
            <>
              <NavLink to="/profile" className={linkClass}>My Profile</NavLink>
              <button onClick={handleLogout} className="btn-secondary mt-2">Logout</button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={linkClass}>Login</NavLink>
              <NavLink to="/register" className={linkClass}>Register</NavLink>
            </>
          )}
        </nav>
      )}
    </header>
  )
}
