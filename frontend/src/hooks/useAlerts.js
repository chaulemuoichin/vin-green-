import { useState, useEffect, useCallback } from 'react'

export function useAlerts() {
  const [alerts, setAlerts] = useState([])

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch('/api/alerts')
      if (!res.ok) return
      setAlerts(await res.json())
    } catch {}
  }, [])

  const dismiss = useCallback(async (id) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, dismissed: true } : a))
    try {
      await fetch('/api/alerts/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      })
    } catch {}
  }, [])

  useEffect(() => {
    fetchAlerts()
    const id = setInterval(fetchAlerts, 10000)
    return () => clearInterval(id)
  }, [fetchAlerts])

  return { alerts, dismiss }
}
