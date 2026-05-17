import { useState, useEffect, useCallback } from 'react'

export function useAQI() {
  const [current, setCurrent] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState(null)

  const fetchCurrent = useCallback(async () => {
    try {
      const res = await fetch('/api/sensor/current')
      if (!res.ok) throw new Error('sensor fetch failed')
      setCurrent(await res.json())
    } catch (e) {
      setError(e.message)
    }
  }, [])

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch('/api/sensor/history')
      if (!res.ok) throw new Error('history fetch failed')
      const data = await res.json()
      setHistory(data.map(d => ({
        ...d,
        time: new Date(d.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      })))
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    fetchCurrent()
    fetchHistory()
    const id = setInterval(fetchCurrent, 5000)
    return () => clearInterval(id)
  }, [fetchCurrent, fetchHistory])

  return { current, history, error }
}
