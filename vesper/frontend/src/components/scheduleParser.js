// Parses plain-text timetable into structured events.
// Handles two formats:
//   Day-header style:   "Monday\n09:00-11:00 Calculus\n14:00-16:00 Lab"
//   Inline style:       "Mon 09:00-11:00 Calculus (Room 101)"

const DAY_NAMES = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
const DAY_SHORT = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

function resolveDay(str) {
  const lc = str.toLowerCase().replace(/[.:,\s]+$/, '')
  const full = DAY_NAMES.indexOf(lc)
  if (full !== -1) return full
  const short = DAY_SHORT.indexOf(lc.slice(0, 3))
  return short
}

function parseTimeEntry(timeStr, rest) {
  const m = timeStr.match(/(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})/)
  if (!m) return null
  const [, sh, sm, eh, em] = m
  const startTime = `${sh.padStart(2, '0')}:${sm}`
  const endTime = `${eh.padStart(2, '0')}:${em}`
  const locMatch = rest.trim().match(/^(.+?)\s*\((.+)\)\s*$/)
  const title = locMatch ? locMatch[1].trim() : rest.trim()
  const location = locMatch ? locMatch[2].trim() : null
  return { startTime, endTime, title, location }
}

export function parseSchedule(text) {
  if (!text) return []
  const events = []
  let currentDay = -1

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue

    // Check for day header (just a day name on its own line)
    const dayIdx = resolveDay(line)
    if (dayIdx !== -1 && !/\d/.test(line)) {
      currentDay = dayIdx
      continue
    }

    // Inline: "Mon 09:00-11:00 Title" or "Monday 09:00-11:00 Title"
    const inlineMatch = line.match(
      /^([A-Za-z]+)\s+(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})\s+(.+)/
    )
    if (inlineMatch) {
      const dIdx = resolveDay(inlineMatch[1])
      if (dIdx !== -1) {
        const entry = parseTimeEntry(inlineMatch[2], inlineMatch[3])
        if (entry) events.push({ day: dIdx, ...entry })
        continue
      }
    }

    // Under-header: "09:00-11:00 Title"
    if (currentDay >= 0) {
      const underMatch = line.match(/^(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})\s+(.+)/)
      if (underMatch) {
        const entry = parseTimeEntry(underMatch[1], underMatch[2])
        if (entry) events.push({ day: currentDay, ...entry })
      }
    }
  }

  return events
}

export function timeToMinutes(t) {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

export function getDayName(idx) {
  return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][idx] ?? ''
}

export function getDayShort(idx) {
  return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][idx] ?? ''
}
