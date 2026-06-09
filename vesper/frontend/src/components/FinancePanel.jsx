import { useState, useEffect } from 'react'
import './panels.css'

export default function FinancePanel({ onLog, onLoadSummary }) {
  const [amount, setAmount]     = useState('')
  const [category, setCategory] = useState('')
  const [note, setNote]         = useState('')
  const [result, setResult]     = useState(null)
  const [summary, setSummary]   = useState('')
  const [error, setError]       = useState('')

  useEffect(() => {
    onLoadSummary().then((r) => { if (r) setSummary(r.summary) }).catch(() => {})
  }, [onLoadSummary])

  async function submit(e) {
    e.preventDefault()
    const amt = parseFloat(amount)
    if (!(amt > 0)) { setError('Amount must be positive'); return }
    if (!category.trim()) { setError('Category is required'); return }
    setError('')
    try {
      const r = await onLog(amt, category.trim(), note.trim())
      if (!r) return
      setResult(r)
      setAmount(''); setCategory(''); setNote('')
      const s = await onLoadSummary()
      if (s) setSummary(s.summary)
    } catch {
      setError('Could not log expense')
    }
  }

  return (
    <div className="panel">
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <input
          className="panel-input"
          type="number"
          placeholder="Amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          min="0"
          step="0.01"
        />
        <input
          className="panel-input"
          placeholder="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
        <input
          className="panel-input"
          placeholder="Note (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button type="submit" className="panel-btn">
          Log expense
        </button>
      </form>

      {error && <p className="panel-err">{error}</p>}

      {result && (
        <div className="finance-result">
          Logged · month total {result.currency} {result.month_total}
          <br />
          {result.currency} {result.category_total} in {result.category || category}
        </div>
      )}

      {summary && <pre className="finance-summary">{summary}</pre>}
    </div>
  )
}
