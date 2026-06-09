import './panels.css'

const PRIORITY_COLOR = {
  urgent: 'var(--ctp-red)',
  high:   'var(--ctp-peach)',
  normal: 'var(--ctp-blue)',
  low:    'var(--ctp-overlay0)',
}

const KIND_LABEL = {
  deadline_overdue: 'Overdue',
  deadline_24h:     '24h left',
  deadline_72h:     '72h left',
  next3:            'Upcoming',
  lecture_new:      'Lecture saved',
  morning_digest:   'Morning digest',
  evening_nudge:    'Evening nudge',
  daily_digest:     'Daily digest',
  heartbeat_tick:   'System degraded',
  error:            'Error',
  pr_opened:        'PR opened',
  pr_merged:        'PR merged',
  pr_comment:       'PR comment',
}

function fmtTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' }) + ' KL'
  } catch {
    return ''
  }
}

export default function FeedPanel({ items, markRead }) {
  if (!items || !items.length) {
    return (
      <div className="panel-empty" style={{ padding: '28px 16px' }}>
        No alerts yet.
        <span style={{ fontSize: 11 }}>
          Heartbeat outputs will appear here.
        </span>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="feed-list">
        {items.map(item => {
          const color = item.read
            ? 'var(--muted)'
            : (PRIORITY_COLOR[item.priority] || PRIORITY_COLOR.low)
          return (
            <div
              key={item.id}
              data-testid={`feed-item-${item.id}`}
              className="feed-item"
              data-read={item.read}
              style={{ '--feed-color': color }}
              onClick={() => !item.read && markRead(item.id)}
            >
              <div className="feed-dot" />
              <div className="feed-body-wrap">
                <div className="feed-kind">
                  {KIND_LABEL[item.kind] || item.kind}
                </div>
                <div className="feed-title">{item.title}</div>
                {item.body && (
                  <div className="feed-preview">{item.body}</div>
                )}
                <div className="feed-time">{fmtTime(item.created_at)}</div>
              </div>
            </div>
          )
        })}
      </div>
      <div className="feed-footer">
        Last 50 items · click to mark read
      </div>
    </div>
  )
}
