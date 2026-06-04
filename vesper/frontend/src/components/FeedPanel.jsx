const PRIORITY_BORDER = {
  urgent: '#E74C3C',
  high: '#E67E22',
  normal: '#3498DB',
  low: '#95A5A6',
}

const KIND_LABEL = {
  deadline_overdue: '🔴 Overdue',
  deadline_24h: '⚠ 24h Deadline',
  deadline_72h: '⏰ 72h Deadline',
  next3: '📋 Deadlines',
  lecture_new: '📚 Lecture saved',
  morning_digest: '🌅 Morning digest',
  evening_nudge: '🌙 Evening nudge',
  daily_digest: '📝 Daily digest',
  heartbeat_tick: '🔴 System degraded',
  error: '🔴 Error',
  pr_opened: '🟢 PR opened',
  pr_merged: '🟣 PR merged',
  pr_comment: '💬 PR comment',
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
      <div style={{ padding: 12, fontSize: 11, color: 'var(--dim)' }}>
        No alerts yet — heartbeat outputs will appear here.
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 4, padding: 8 }}>
        {items.map(item => {
          const border = PRIORITY_BORDER[item.priority] || PRIORITY_BORDER.low
          const dimmed = item.read
          return (
            <div
              key={item.id}
              data-testid={`feed-item-${item.id}`}
              onClick={() => !dimmed && markRead(item.id)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 8,
                borderLeft: `3px solid ${dimmed ? '#2a2a2a' : border}`,
                padding: '6px 10px',
                background: dimmed ? '#111' : 'rgba(255,255,255,0.02)',
                borderRadius: '0 4px 4px 0',
                opacity: dimmed ? 0.45 : 1,
                cursor: dimmed ? 'default' : 'pointer',
              }}
            >
              <div style={{
                width: 7, height: 7, borderRadius: '50%', flexShrink: 0, marginTop: 4,
                background: dimmed ? '#2a2a2a' : border,
              }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.68rem', color: dimmed ? '#555' : border, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {KIND_LABEL[item.kind] || item.kind}
                </div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: dimmed ? '#666' : '#eee', margin: '2px 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.title}
                </div>
                {item.body && (
                  <div style={{ fontSize: '0.7rem', color: dimmed ? '#555' : '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.body}
                  </div>
                )}
                <div style={{ fontSize: '0.63rem', color: dimmed ? '#444' : '#555', marginTop: 3 }}>
                  {fmtTime(item.created_at)}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <div style={{ padding: '6px 12px', fontSize: '0.63rem', color: '#444', borderTop: '1px solid var(--line)' }}>
        Keeps last 50 items · click any item to mark read
      </div>
    </div>
  )
}
