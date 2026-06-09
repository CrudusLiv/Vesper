import { useMemo } from 'react'
import { parseSchedule, timeToMinutes, getDayShort } from './scheduleParser.js'
import './ScheduleCalendar.css'

const DAY_START = 8   // 08:00
const DAY_END = 22    // 22:00
const SLOT_HEIGHT = 28 // px per hour
const PALETTE = [
  'rgba(137,220,235,0.22)',
  'rgba(180,190,254,0.22)',
  'rgba(245,197,99,0.22)',
  'rgba(203,166,247,0.22)',
  'rgba(166,227,161,0.22)',
]

function eventColor(idx) {
  return PALETTE[idx % PALETTE.length]
}

export default function ScheduleCalendar({ scheduleText }) {
  const events = useMemo(() => parseSchedule(scheduleText), [scheduleText])

  const totalMinutes = (DAY_END - DAY_START) * 60
  const totalHeight = (DAY_END - DAY_START) * SLOT_HEIGHT

  function topPct(time) {
    const mins = timeToMinutes(time) - DAY_START * 60
    return `${(mins / totalMinutes) * 100}%`
  }

  function heightPct(start, end) {
    const dur = timeToMinutes(end) - timeToMinutes(start)
    return `${(dur / totalMinutes) * 100}%`
  }

  const hours = []
  for (let h = DAY_START; h <= DAY_END; h += 2) {
    hours.push(h)
  }

  return (
    <div className="sched-cal" aria-label="weekly schedule calendar">
      <div className="sched-cal-header">
        <div className="sched-cal-time-gutter" />
        {Array.from({ length: 7 }, (_, i) => (
          <div key={i} className="sched-cal-day-label">{getDayShort(i)}</div>
        ))}
      </div>

      <div className="sched-cal-body">
        <div className="sched-cal-time-col">
          {hours.map(h => (
            <div
              key={h}
              className="sched-cal-hour-label"
              style={{ top: `${((h - DAY_START) / (DAY_END - DAY_START)) * 100}%` }}
            >
              {String(h).padStart(2, '0')}
            </div>
          ))}
        </div>

        {Array.from({ length: 7 }, (_, day) => {
          const dayEvents = events.filter(e => e.day === day)
          return (
            <div key={day} className="sched-cal-day-col">
              {hours.slice(0, -1).map(h => (
                <div key={h} className="sched-cal-slot" style={{ height: SLOT_HEIGHT }} />
              ))}
              {dayEvents.map((ev, i) => (
                <div
                  key={i}
                  className="sched-cal-event"
                  style={{
                    top: topPct(ev.startTime),
                    height: heightPct(ev.startTime, ev.endTime),
                    background: eventColor(i),
                    minHeight: 18,
                  }}
                  title={`${ev.startTime}–${ev.endTime} ${ev.title}${ev.location ? ` (${ev.location})` : ''}`}
                >
                  <span className="sched-cal-event-title">{ev.title}</span>
                  <span className="sched-cal-event-time">{ev.startTime}</span>
                </div>
              ))}
            </div>
          )
        })}
      </div>

      {events.length === 0 && (
        <div className="sched-cal-empty">No events parsed yet.</div>
      )}
    </div>
  )
}
