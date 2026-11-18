import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../services/api'

/** Run an async loader on mount (and when deps change). Returns { data, error, loading, reload, setData }. */
export function useAsync(loader, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const mounted = useRef(true)

  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await loader()
      if (mounted.current) setData(res?.data ?? res)
    } catch (err) {
      if (mounted.current) setError(errorMessage(err))
    } finally {
      if (mounted.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    mounted.current = true
    reload()
    return () => { mounted.current = false }
  }, [reload])

  return { data, error, loading, reload, setData }
}
