import { useEffect, useState } from 'react'

const PREFIX = 'ai:'

/**
 * useState that survives navigation (Back button) for the current browser tab.
 * Stored in sessionStorage, so it disappears when the tab closes; clearSessionState() runs on logout.
 */
export function useSessionState(key, initial) {
  const fullKey = PREFIX + key
  const [value, setValue] = useState(() => {
    try {
      const raw = sessionStorage.getItem(fullKey)
      return raw === null ? initial : JSON.parse(raw)
    } catch {
      return initial
    }
  })
  useEffect(() => {
    try { sessionStorage.setItem(fullKey, JSON.stringify(value)) } catch { /* storage full or blocked */ }
  }, [fullKey, value])
  return [value, setValue]
}

export function clearSessionState() {
  try {
    Object.keys(sessionStorage).filter((k) => k.startsWith(PREFIX)).forEach((k) => sessionStorage.removeItem(k))
  } catch { /* storage blocked */ }
}
