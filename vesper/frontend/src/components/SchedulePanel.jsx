import { useState, useEffect } from 'react'
import { ConflictError } from '../api/client.js'
import ScheduleCalendar from './ScheduleCalendar.jsx'
import ScheduleTimeline from './ScheduleTimeline.jsx'
import './panels.css'

const VIEWS = ['Timeline', 'Calendar', 'Edit']

export default function SchedulePanel({ onLoad, onSave }) {
  const [current, setCurrent]   = useState(null)
  const [text, setText]         = useState('')
  const [conflict, setConflict] = useState(null)
  const [status, setStatus]     = useState('')
  const [view, setView]         = useState('Timeline')

  useEffect(() => {
    onLoad().then((r) => { if (r) setCurrent(r.schedule) }).catch(() => {})
  }, [onLoad])

  async function save(confirm) {
    if (!text.trim()) return
    setStatus('')
    try {
      const r = await onSave(text, confirm)
      if (!r) return
      setConflict(null); setText(''); setStatus('saved')
      const fresh = await onLoad()
      if (fresh) setCurrent(fresh.schedule)
      setView('Timeline')
    } catch (err) {
      if (err instanceof ConflictError) { setConflict(err.data); return }
      setStatus('error')
    }
  }

  return (
    <div className="panel">
      <div className="schedule-view-switch">
        {VIEWS.map(v => (
          <button
            key={v}
            className="schedule-view-btn"
            data-active={view === v}
            onClick={() => setView(v)}
          >
            {v}
          </button>
        ))}
      </div>

      {view === 'Timeline' && <ScheduleTimeline scheduleText={current} />}
      {view === 'Calendar' && <ScheduleCalendar scheduleText={current} />}

      {view === 'Edit' && (
        <>
          {current && (
            <pre className="schedule-current">{current}</pre>
          )}
          {!current && (
            <p className="panel-hint">No schedule set yet. Paste your timetable below.</p>
          )}

          <form
            onSubmit={(e) => { e.preventDefault(); save(false) }}
            style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          >
            <textarea
              className="panel-textarea"
              placeholder="Paste your timetable…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
            />
            <button type="submit" disabled={!text.trim()} className="panel-btn">
              Set schedule
            </button>
          </form>

          {conflict && (
            <div className="schedule-conflict">
              <p className="schedule-conflict-label">
                A schedule already exists. Replace with:
              </p>
              <pre className="schedule-conflict-summary">{conflict.summary}</pre>
              <div className="schedule-conflict-actions">
                <button
                  type="button"
                  onClick={() => save(true)}
                  className="schedule-conflict-replace"
                >
                  Replace
                </button>
                <button
                  type="button"
                  onClick={() => setConflict(null)}
                  className="panel-btn-ghost"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {status === 'saved' && <p className="panel-ok">Schedule saved</p>}
          {status === 'error' && <p className="panel-err">Could not parse timetable</p>}
        </>
      )}
    </div>
  )
}
