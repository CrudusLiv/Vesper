import { useState, useCallback } from 'react'
import { api } from '../api/client.js'

export function useSettings() {
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getSettings()
      setSettings(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const save = useCallback(async (updates) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.saveSettings(updates)
      setSettings(data)
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { settings, loading, error, load, save }
}
