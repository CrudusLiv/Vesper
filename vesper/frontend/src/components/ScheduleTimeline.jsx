import { useMemo } from 'react'
import { parseSchedule, timeToMinutes, getDayName } from './scheduleParser.js'
import './ScheduleTimeline.css'

export default function ScheduleTimeline({ scheduleText }) {
  const events = useMemo(() => {
    const parsed = parseSchedule(scheduleText)
    return parsed.slice().sort((a, b) => {
      if (a.day !== b.day) return a.day - b.day
      return timeToMinutes(a.startTime) - timeToMinutes(b.startTime)
    })
  }, [scheduleText])

  const grouped = useMemo(() => {
    const map = new Map()
    for (const ev of events) {
      if (!map.has(ev.day)) map.set(ev.day, [])
      map.get(ev.day).push(ev)
    }
    return [...map.entries()].sort(([a], [b]) => a - b)
  }, [events])

  if (grouped.length === 0) {
    return <div className="sched-tl-empty">No events parsed yet.</div>
  }

  return (
    <div className="sched-tl" aria-label="weekly schedule timeline">
      {grouped.map(([day, dayEvents]) => (
        <div key={day} className="sched-tl-day">
          <div className="sched-tl-day-label">{getDayName(day)}</div>
          <div className="sched-tl-events">
            {dayEvents.map((ev, i) => {
              const startMins = timeToMinutes(ev.startTime)
              const endMins = timeToMinutes(ev.endTime)
              const dur = endMins - startMins
              const hours = Math.floor(dur / 60)
              const mins = dur % 60
              const durStr = hours > 0
                ? `${hours}h${mins > 0 ? ` ${mins}m` : ''}`
                : `${mins}m`

              return (
                <div key={i} className="sched-tl-event">
                  <div className="sched-tl-time">
                    <span className="sched-tl-start">{ev.startTime}</span>
                    <span className="sched-tl-dur">{durStr}</span>
                  </div>
                  <div className="sched-tl-details">
                    <span className="sched-tl-title">{ev.title}</span>
                    {ev.location && (
                      <span className="sched-tl-location">{ev.location}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
