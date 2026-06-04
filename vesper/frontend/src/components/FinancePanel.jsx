import { useState, useEffect } from 'react'

const inputStyle = { background: '#0b0f15', border: '1px solid var(--line)', borderRadius: 6, padding: '6px 8px', fontSize: 12, color: 'var(--ink)' }

export default function FinancePanel({ onLog, onLoadSummary }) {
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('')
  const [note, setNote] = useState('')
  const [result, setResult] = useState(null)
  const [summary, setSummary] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    onLoadSummary().then((r) => { if (r) setSummary(r.summary) }).catch(() => {})
  }, [onLoadSummary])

  async function submit(e) {
    e.preventDefault()
    const amt = parseFloat(amount)
    if (!(amt > 0)) { setError('amount must be positive'); return }
    if (!category.trim()) { setError('category required'); return }
    setError('')
    try {
      const r = await onLog(amt, category.trim(), note.trim())
      if (!r) return
      setResult(r)
      setAmount(''); setCategory(''); setNote('')
      const s = await onLoadSummary()
      if (s) setSummary(s.summary)
    } catch {
      setError('could not log expense')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dim)' }}>Finance</div>
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <input className="mono" placeholder="amount" value={amount} onChange={(e) => setAmount(e.target.value)} style={inputStyle} />
        <input className="mono" placeholder="category" value={category} onChange={(e) => setCategory(e.target.value)} style={inputStyle} />
        <input className="mono" placeholder="note (optional)" value={note} onChange={(e) => setNote(e.target.value)} style={inputStyle} />
        <button type="submit" style={{ ...inputStyle, cursor: 'pointer', borderColor: 'var(--accent)', color: 'var(--accent2)' }}>Log expense</button>
      </form>
      {error && <div className="mono" style={{ fontSize: 10, color: 'var(--led-off)' }}>{error}</div>}
      {result && (
        <div className="mono" style={{ fontSize: 10, color: 'var(--dim)' }}>
          logged · month {result.currency} {result.month_total} · {result.currency} {result.category_total} in category
        </div>
      )}
      {summary && <pre className="mono" style={{ fontSize: 10, color: 'var(--dim)', whiteSpace: 'pre-wrap', margin: 0 }}>{summary}</pre>}
    </div>
  )
}
