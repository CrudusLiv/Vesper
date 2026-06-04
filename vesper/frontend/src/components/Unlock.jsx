import { useState } from 'react'
import { api, AuthError } from '../api/client.js'

export default function Unlock({ onUnlock }) {
  const [secret, setSecret] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.status(secret)
      onUnlock(secret)
    } catch (err) {
      setError(err instanceof AuthError ? 'Incorrect secret.' : 'Could not reach Vesper.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center' }}>
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12, width: 280 }}>
        <div className="mono" style={{ letterSpacing: '0.2em', color: 'var(--accent2)', fontWeight: 700 }}>VESPER</div>
        <input
          type="password"
          placeholder="API secret"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          className="mono"
          style={{ padding: '8px 10px', background: '#0b0f15', border: '1px solid var(--line)', borderRadius: 6, color: 'var(--ink)' }}
        />
        <button
          type="submit"
          disabled={busy || !secret}
          style={{ padding: '8px 10px', background: 'var(--accent)', color: '#fff', border: 0, borderRadius: 6, cursor: 'pointer' }}
        >
          {busy ? 'Unlocking…' : 'Unlock'}
        </button>
        {error && <div style={{ color: 'var(--led-off)', fontSize: 12 }}>{error}</div>}
      </form>
    </div>
  )
}
