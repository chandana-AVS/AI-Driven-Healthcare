import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { clearSessionState } from '../hooks/useSessionState'
import { authApi, setUnauthorizedHandler, tokenStore, userApi } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(tokenStore.get()))
  const [sessionMessage, setSessionMessage] = useState('')

  const logout = useCallback((message = '') => {
    clearSessionState()  // forget AI results so the next person on a shared phone cannot see them
    tokenStore.set(null)
    setUser(null)
    setSessionMessage(message)
  }, [])

  const refreshUser = useCallback(async () => {
    const { data } = await userApi.me()
    setUser(data)
    return data
  }, [])

  useEffect(() => {
    setUnauthorizedHandler((detail) => {
      setUser(null)
      setSessionMessage(detail === 'Token has expired' ? 'Your session expired. Please log in again.' : 'Please log in again.')
    })
    if (tokenStore.get()) {
      refreshUser().catch(() => logout()).finally(() => setLoading(false))
    }
  }, [refreshUser, logout])

  const login = useCallback(async (identifier, password) => {
    const { data } = await authApi.login(identifier, password)
    tokenStore.set(data.access_token)
    setSessionMessage('')
    return refreshUser()
  }, [refreshUser])

  const value = useMemo(
    () => ({ user, setUser, loading, login, logout, refreshUser, sessionMessage, setSessionMessage }),
    [user, loading, login, logout, refreshUser, sessionMessage],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
