---
cssclasses:
  - dashboard
---

```dataviewjs
const now      = new Date();
const monthKey = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
const monthLabel = now.toLocaleDateString("en-MY",{month:"long",year:"numeric"}).toUpperCase();
const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;
const nowHHMM  = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}`;
const dateStr  = now.toLocaleDateString("en-MY",{weekday:"long",year:"numeric",month:"long",day:"numeric"});
const BUDGET   = 1500;

// ── pre-fetch all vault files in parallel ─────────────────────────────────────
const [dlRaw, projRaw, gcalRaw, hbRaw, habitsRaw, finRaw, layoutRaw, logRaw, pingsRaw] = await Promise.all([
  dv.io.load("DEADLINES.md"),
  dv.io.load("PROJECTS.md"),
  dv.io.load("state/gcal-today.md"),
  dv.io.load("state/heartbeat-state.json"),
  dv.io.load("HABITS.md"),
  dv.io.load(`finance/${monthKey}.md`),
  dv.io.load("state/dashboard-layout.json"),
  dv.io.load("state/refresh-log.md"),
  dv.io.load("state/discord-pings.md"),
]);

// ── LAYOUT ────────────────────────────────────────────────────────────────────
const DEFAULT_LAYOUT = {
  columns: [
    ["focus", "tasks", "inbox", "finance"],
    ["schedule", "pillars", "recent", "capture", "heartbeat"]
  ],
  hidden: [],
  columnWidths: ["1.4fr", "1fr"]
};
let layout = DEFAULT_LAYOUT;
try { if (layoutRaw) layout = JSON.parse(layoutRaw); } catch {}
window.__dbLayout = JSON.parse(JSON.stringify(layout)); // in-memory copy for edit mode
window.__dbEditMode = false; // reset on each render

// ── CURRENT FOCUS ─────────────────────────────────────────────────────────────
const dlLines = (dlRaw||"").split("\n").filter(l => /^\d{4}-\d{2}-\d{2}/.test(l.trim()));
const futureDeadlines = dlLines
  .map(l => { const m = l.match(/^(\d{4}-\d{2}-\d{2})\s*[—–-]\s*(.+?)\s*[—–-]\s*(.+)/); return m ? {date:new Date(m[1]+"T00:00:00"),course:m[2].trim(),title:m[3].trim()} : null; })
  .filter(d => d && d.date >= new Date(now.getFullYear(), now.getMonth(), now.getDate()))
  .sort((a,b) => a.date - b.date);

let focusTitle = "No active focus", focusSubtitle = "Add deadlines to DEADLINES.md", focusMilestone = "", focusNext = "", focusColor = "var(--text-muted)";
if (futureDeadlines.length > 0) {
  const nd = futureDeadlines[0];
  const h = (nd.date - now) / 36e5;
  focusTitle     = nd.title;
  focusSubtitle  = `${nd.course} · due ${nd.date.toLocaleDateString("en-MY",{month:"short",day:"numeric"})}`;
  focusMilestone = nd.date.toLocaleDateString("en-MY",{month:"short",day:"numeric"});
  focusNext      = h <= 24 ? "Due soon!" : h <= 72 ? "Due in 3 days" : "Upcoming";
  focusColor     = h <= 24 ? "#f85149" : h <= 72 ? "#d29922" : "var(--text-muted)";
} else {
  const pm = (projRaw||"").match(/- \*\*(.+?)\*\*\s*[—–-]\s*(.+)/);
  if (pm) { focusTitle = pm[1].trim(); focusSubtitle = pm[2].split(".")[0].trim(); focusMilestone = "Active"; focusNext = "In progress"; }
}

// ── TODAY'S TASKS ─────────────────────────────────────────────────────────────
const TASK_EXCLUDE = ["HABITS", "HEARTBEAT", "SOUL", "DEADLINES", "PROJECTS", "MEMORY", "HOME", "state/", ".obsidian"];
const allTasks = dv.pages()
  .where(p => !TASK_EXCLUDE.some(x => p.file.path.includes(x)))
  .file.tasks.where(t => !t.completed);
const topTasks = [...allTasks.sort(t => t.due?.ts ?? Number.MAX_SAFE_INTEGER, "asc")].slice(0, 5);
function dotColor(t) {
  if (!t.due) return "#a371f7";
  const diff = (t.due.ts - now.getTime()) / 864e5;
  return diff < 0 ? "#f85149" : diff < 1 ? "#d29922" : "#a371f7";
}
function cleanText(raw) {
  return String(raw).replace(/\[.*?\]/g,"").replace(/\*\*(.+?)\*\*/g,"$1").replace(/_([^_]+)_/g,"$1").trim();
}
const taskRows = topTasks.map(t =>
  `<div style="display:flex;align-items:center;gap:8px;background:var(--background-primary);border-radius:4px;padding:7px 10px;cursor:pointer" onclick="window._dbOpenNote('${t.path}')">` +
  `<div style="width:6px;height:6px;border-radius:50%;background:${dotColor(t)};flex-shrink:0"></div>` +
  `<span style="font-size:0.9em">${cleanText(t.text)}</span></div>`
).join("");

// ── INBOX ─────────────────────────────────────────────────────────────────────
const discordPage = dv.page("state/discord-recent");
const githubPage  = dv.page("state/github-counts");
const discordDMs  = discordPage?.unread_dms ?? "_";
const githubPRs   = githubPage?.prs_open   ?? "_";
const vaultInbox  = dv.pages('"inbox"').where(p => !p.file.path.includes("_processed")).length;

// ── FINANCE ───────────────────────────────────────────────────────────────────
let finHTML = `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No data for ${monthKey}</div>`;
if (finRaw) {
  const totalMatch = finRaw.match(/\[!summary\]\s*RM\s*([\d,]+)/);
  const total      = totalMatch ? parseFloat(totalMatch[1].replace(/,/g,"")) : 0;
  const pct        = Math.min(100, Math.round(total / BUDGET * 100));
  const catRows    = [...finRaw.matchAll(/\|\s+`(\w+)`\s+\|\s+RM\s+([\d,]+)\s+\|\s+([\d.]+)%/g)]
    .map(m => ({name:m[1], amt:parseFloat(m[2].replace(/,/g,"")), pct:parseInt(m[3])}));
  finHTML = `
    <div style="display:flex;justify-content:flex-end;align-items:baseline;margin-bottom:7px">
      <span style="font-weight:700;font-size:14px">RM ${total.toLocaleString()} <span style="color:var(--text-muted);font-weight:400;font-size:0.75rem">/ ${BUDGET}</span></span>
    </div>
    <div style="background:var(--background-modifier-border);height:4px;border-radius:2px;margin-bottom:9px">
      <div class="db-bar-fill" style="width:${pct}%;height:100%"></div>
    </div>
    ${catRows.map(c =>
      `<div style="margin-bottom:6px">` +
      `<div style="display:flex;justify-content:space-between;font-size:0.8em;margin-bottom:2px"><span>${c.name}</span><span style="color:var(--db-accent)">RM ${c.amt.toLocaleString()} · ${c.pct}%</span></div>` +
      `<div style="background:var(--background-modifier-border);height:3px;border-radius:2px"><div class="db-bar-cat" style="width:${c.pct}%;height:100%"></div></div></div>`
    ).join("")}`;
}

// ── TODAY'S SCHEDULE ──────────────────────────────────────────────────────────
const events = [];
if (gcalRaw) {
  for (const l of gcalRaw.split("\n").filter(l => /^- \d{2}:\d{2}/.test(l.trim()))) {
    const m = l.match(/^- (\d{2}:\d{2})[^:]*:\s*(.+)/);
    if (m) events.push({time:m[1], title:m[2].trim(), subtitle:"GCal"});
  }
}
for (const l of dlLines.filter(l => l.startsWith(todayStr))) {
  const m = l.match(/\d{4}-\d{2}-\d{2}\s*[—–-]\s*(.+?)\s*[—–-]\s*(.+)/);
  if (m) events.push({time:"00:00", title:m[2].trim(), subtitle:m[1].trim()+" · Due today"});
}
events.sort((a,b) => a.time.localeCompare(b.time));
let nowIdx = -1;
for (let i=0;i<events.length;i++) { if (events[i].time <= nowHHMM) nowIdx = i; }
const schedRows = events.map((ev,i) => {
  const isNow = i === nowIdx;
  return `<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid var(--background-modifier-border)${isNow?";background:rgba(var(--db-accent-rgb),.06);margin:0 -4px;padding-left:4px":""}">` +
    `<span class="db-time"${isNow?' style="color:var(--db-accent)"':''}>${isNow?"Now":ev.time}</span>` +
    `<div><div style="font-size:0.9em${isNow?";font-weight:600":""}">${ev.title}</div>` +
    `<div style="font-size:0.78rem;color:${isNow?"var(--db-accent)":"var(--text-muted)"}">${ev.subtitle}</div></div></div>`;
}).join("") || `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No events today</div>`;
const gcalNote = gcalRaw ? "" : `<div style="margin-top:7px;color:var(--text-muted);font-size:0.7rem;font-style:italic">+ GCal events once OAuth is configured</div>`;

// ── RECENT NOTES ─────────────────────────────────────────────────────────────
const NOTE_EXCLUDE = ["HOME", "SOUL", "DEADLINES", "PROJECTS", "MEMORY", "HEARTBEAT", "HABITS", ".obsidian", "state/", "inbox/_processed", "finance/"];
const recentNotes = dv.pages()
  .where(p => !NOTE_EXCLUDE.some(x => p.file.path.includes(x)) && p.file.name !== "HOME")
  .sort(p => p.file.mtime, "desc")
  .limit(5);
const recentHTML = recentNotes.length === 0
  ? `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No notes yet</div>`
  : [...recentNotes].map(p => {
      const when = p.file.mtime.toFormat("HH:mm");
      return `<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.8em;margin-bottom:5px">` +
        `<span style="color:var(--db-accent);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;cursor:pointer" onclick="window._dbOpenNote('${p.file.path}')">${p.file.name}</span>` +
        `<span style="color:var(--text-muted);font-size:0.75rem;flex-shrink:0;margin-left:8px">${when}</span></div>`;
    }).join("");

// ── DAILY PILLARS ─────────────────────────────────────────────────────────────
let pillarsHTML;
const habitsPage = dv.page("HABITS");
if (!habitsPage) {
  pillarsHTML = `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">HABITS.md not found</div>`;
} else if (habitsRaw && habitsRaw.includes("Stub — paused")) {
  pillarsHTML = `<div style="color:var(--db-accent);font-style:italic;font-size:0.85em">Paused — resumes June 2026</div>`;
} else {
  const ht = habitsPage.file.tasks;
  pillarsHTML = ht.length === 0
    ? `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No habits defined</div>`
    : [...ht].map(t => `<div style="display:flex;align-items:center;gap:8px;font-size:0.9em;margin-bottom:6px"><span>${t.completed?"✅":"◻"}</span><span>${String(t.text)}</span></div>`).join("");
}

// ── STATUS ────────────────────────────────────────────────────────────────────
let hbHTML = "";
if (!hbRaw && !logRaw) {
  hbHTML = `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No data yet — click Refresh</div>`;
} else {
  let hs = null;
  if (hbRaw) { try { hs = JSON.parse(hbRaw); } catch {} }

  if (hs) {
    const lastTs = hs.timestamp ? new Date(hs.timestamp * 1000) : null;
    const mAgo   = lastTs ? Math.round((now - lastTs) / 6e4) : null;

    const pingCount = (pingsRaw || "").match(/^ping_count:\s*(\d+)/m)?.[1] ?? "—";

    const intRows = [
      {key:"discord", label:"Discord pings", detail:hs.discord?.error ?? `${pingCount}`, ok: !hs.discord?.error},
      {key:"github",  label:"GitHub",        detail:hs.github?.error  ?? `${hs.github?.push_count??0} pushes`, ok: !hs.github?.error},
      {key:"inbox",   label:"Inbox",         detail:hs.inbox?.error   ?? `${hs.inbox?.count??0} files`, ok: !hs.inbox?.error},
    ].map(r =>
      `<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.82em;padding:5px 0;border-bottom:1px solid var(--background-modifier-border)">` +
      `<span style="display:flex;align-items:center;gap:7px"><span style="width:8px;height:8px;border-radius:50%;background:${r.ok?"#3fb950":"#f85149"};flex-shrink:0"></span>${r.label}</span>` +
      `<span style="color:${r.ok?"#3fb950":"#f85149"};font-weight:600">${r.detail}</span></div>`
    ).join("");

    function nextRun(from) {
      const c = new Date(from.getTime() + 30 * 6e4);
      const hhmm = c.getHours() * 60 + c.getMinutes();
      if (hhmm >= 9*60 && hhmm < 22*60) return c;
      const next = new Date(c);
      if (hhmm >= 22*60) next.setDate(next.getDate() + 1);
      next.setHours(9, 0, 0, 0);
      return next;
    }
    const nextTs   = lastTs ? nextRun(lastTs) : null;
    const mUntil   = nextTs ? Math.round((nextTs - now) / 6e4) : null;
    const nextLabel = mUntil === null ? "unknown"
      : mUntil <= 0  ? "overdue"
      : mUntil < 60  ? `in ${mUntil}m`
      : `at ${nextTs.toLocaleTimeString("en-MY",{hour:"2-digit",minute:"2-digit",hour12:false})}`;

    hbHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
        <div style="background:var(--background-primary);border-radius:6px;padding:9px 11px">
          <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:3px">Last ran</div>
          <div style="font-size:1em;font-weight:700">${lastTs ? lastTs.toLocaleTimeString("en-MY",{hour:"2-digit",minute:"2-digit",hour12:false}) : "—"}</div>
          <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px">${mAgo !== null ? `${mAgo}m ago` : ""}</div>
        </div>
        <div style="background:var(--background-primary);border-radius:6px;padding:9px 11px">
          <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:3px">Next run</div>
          <div style="font-size:1em;font-weight:700;color:var(--db-accent)">${nextTs ? nextTs.toLocaleTimeString("en-MY",{hour:"2-digit",minute:"2-digit",hour12:false}) : "—"}</div>
          <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px">${nextLabel}</div>
        </div>
      </div>
      ${intRows}`;
  }

  if (logRaw) {
    const logLines = logRaw.split("\n")
      .filter(l => l.trim() && !l.startsWith("---") && !l.startsWith("updated:"));
    if (logLines.length) {
      hbHTML += `<div style="margin-top:10px;font-family:monospace;font-size:0.78em;color:var(--text-muted);background:var(--background-primary);border-radius:4px;padding:8px 10px;white-space:pre-wrap">${logLines.join("\n")}</div>`;
    }
  }
}

// ── CALENDAR ─────────────────────────────────────────────────────────────────
const calYear  = now.getFullYear();
const calMonth = now.getMonth();
const todayDay = now.getDate();

// Build deadline map from ALL deadlines (not just future) so past months show dots
const allDeadlines = dlLines
  .map(l => { const m = l.match(/^(\d{4}-\d{2}-\d{2})\s*[—–-]\s*(.+?)\s*[—–-]\s*(.+)/); return m ? {date:new Date(m[1]+"T00:00:00"),course:m[2].trim(),title:m[3].trim()} : null; })
  .filter(Boolean).sort((a,b) => a.date - b.date);

const dlMap = {};
for (const d of allDeadlines) {
  const k = `${d.date.getFullYear()}-${String(d.date.getMonth()+1).padStart(2,"0")}-${String(d.date.getDate()).padStart(2,"0")}`;
  (dlMap[k] = dlMap[k] || []).push(d);
}

const dayHdrs = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(h =>
  `<div style="text-align:center;font-size:0.6rem;color:var(--text-muted);padding-bottom:6px;font-weight:600">${h}</div>`
).join("");

function makeCalGrid(y, m) {
  const days    = new Date(y, m + 1, 0).getDate();
  const startDow = (new Date(y, m, 1).getDay() + 6) % 7;
  let cells = Array(startDow).fill(`<div></div>`);
  for (let day = 1; day <= days; day++) {
    const k = `${y}-${String(m+1).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
    const isToday = y === calYear && m === calMonth && day === todayDay;
    const hasDl   = (dlMap[k] || []).length > 0;
    cells.push(
      `<div style="text-align:center;padding:3px 1px;border-radius:4px;background:${isToday?"var(--db-accent)":"transparent"};cursor:pointer" onclick="window._dbOpenDay('${k}')">`+
      `<span style="font-size:0.75rem;color:${isToday?"#fff":hasDl?"var(--text-normal)":"var(--text-muted)"};font-weight:${isToday||hasDl?"600":"400"}">${day}</span>`+
      (hasDl&&!isToday?`<div style="width:4px;height:4px;border-radius:50%;background:var(--db-accent);margin:1px auto 0"></div>`:`<div style="height:5px"></div>`)+
      `</div>`
    );
  }
  return `<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:2px">${dayHdrs}</div>`+
         `<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px">${cells.join("")}</div>`;
}

function makeDlList(dls) {
  if (!dls.length) return `<div style="color:var(--text-muted);font-style:italic;font-size:0.8em">No deadlines this month</div>`;
  const today0 = new Date(calYear, calMonth, todayDay);
  return dls.slice(0,8).map(d => {
    const daysLeft = Math.ceil((d.date - today0) / 864e5);
    const urgColor = daysLeft < 0 ? "var(--text-muted)" : daysLeft <= 1 ? "#f85149" : daysLeft <= 3 ? "#d29922" : "var(--text-muted)";
    const label    = daysLeft < 0 ? `${Math.abs(daysLeft)}d ago` : daysLeft === 0 ? "today" : daysLeft === 1 ? "tmrw" : `${daysLeft}d`;
    return `<div style="display:flex;align-items:center;gap:10px;font-size:0.78rem;padding:5px 0;border-bottom:1px solid var(--background-modifier-border);cursor:pointer" onclick="window._dbOpenNote('DEADLINES.md')">`+
      `<span style="color:var(--db-accent);font-weight:700;min-width:28px;text-align:center">${d.date.getDate()}</span>`+
      `<span style="flex:1;color:var(--text-normal)">${d.title}</span>`+
      `<span style="color:var(--text-muted);font-size:0.75rem;white-space:nowrap">${d.course}</span>`+
      `<span style="color:${urgColor};font-size:0.75rem;min-width:42px;text-align:right;font-weight:600">${label}</span>`+
      `</div>`;
  }).join("");
}

// Pre-generate 5 months: 2 back, current, 2 ahead
const CAL_MONTHS = [-2,-1,0,1,2].map(offset => {
  const total = calMonth + offset;
  const y = calYear + Math.floor(total / 12);
  const m = ((total % 12) + 12) % 12;
  const label = new Date(y, m, 1).toLocaleDateString("en-MY",{month:"long",year:"numeric"}).toUpperCase();
  const dls   = allDeadlines.filter(d => d.date.getFullYear()===y && d.date.getMonth()===m);
  return { y, m, label, grid: makeCalGrid(y, m), dls };
});
const CAL_START_IDX = 2; // index of current month

// ── CARD HTML MAP ─────────────────────────────────────────────────────────────
const CARD_HTML = {
  focus: `
    <div class="db-card db-focus" data-id="focus">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1;color:var(--db-accent)">● CURRENT FOCUS</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('focus')">✕</button>
      </div>
      <div style="font-weight:700;font-size:18px;line-height:1.2;margin-bottom:5px">${focusTitle}</div>
      <div style="color:${focusColor};font-size:0.9em;margin-bottom:8px">${focusSubtitle}</div>
      <div style="display:flex;gap:6px">
        ${focusMilestone ? `<span style="background:var(--background-primary);border-radius:3px;padding:3px 9px;font-size:0.75rem;color:var(--db-accent);border:1px solid var(--background-modifier-border)">${focusMilestone}</span>` : ""}
        ${focusNext      ? `<span style="background:var(--background-primary);border-radius:3px;padding:3px 9px;font-size:0.75rem;color:var(--text-muted);border:1px solid var(--background-modifier-border)">${focusNext}</span>` : ""}
      </div>
    </div>`,

  tasks: `
    <div class="db-card" data-id="tasks">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">TODAY'S TASKS</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('tasks')">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:5px">
        ${taskRows || `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No open tasks</div>`}
      </div>
      <div style="margin-top:6px;color:var(--text-muted);font-size:0.78rem">${allTasks.length} open</div>
    </div>`,

  inbox: `
    <div class="db-card" data-id="inbox">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">INBOX</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('inbox')">✕</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px">
        <div class="db-chip" style="padding:10px 8px;text-align:center">
          <div style="color:var(--db-accent);font-size:20px;font-weight:700;line-height:1">${discordDMs}</div>
          <div style="color:var(--text-muted);font-size:0.72rem;margin-top:4px">Discord DMs</div>
        </div>
        <div class="db-chip" style="padding:10px 8px;text-align:center">
          <div style="color:var(--db-accent);font-size:20px;font-weight:700;line-height:1">${githubPRs}</div>
          <div style="color:var(--text-muted);font-size:0.72rem;margin-top:4px">GitHub PRs</div>
        </div>
        <div class="db-chip" style="padding:10px 8px;text-align:center">
          <div style="color:var(--db-accent);font-size:20px;font-weight:700;line-height:1">${vaultInbox}</div>
          <div style="color:var(--text-muted);font-size:0.72rem;margin-top:4px">Vault inbox</div>
        </div>
      </div>
    </div>`,

  finance: `
    <div class="db-card" data-id="finance">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">FINANCE — ${monthLabel}</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('finance')">✕</button>
      </div>
      ${finHTML}
    </div>`,

  schedule: `
    <div class="db-card" data-id="schedule">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">TODAY'S SCHEDULE</div>
        <div style="color:var(--db-accent);font-size:0.78rem;margin-left:8px">${now.toLocaleDateString("en-MY",{day:"numeric",month:"short"})}</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('schedule')">✕</button>
      </div>
      ${schedRows}
      ${gcalNote}
    </div>`,

  pillars: `
    <div class="db-card" data-id="pillars">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">DAILY PILLARS</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('pillars')">✕</button>
      </div>
      ${pillarsHTML}
    </div>`,

  recent: `
    <div class="db-card" data-id="recent">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">RECENT NOTES</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('recent')">✕</button>
      </div>
      ${recentHTML}
    </div>`,

  capture: `
    <div class="db-card" data-id="capture">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">QUICK CAPTURE</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('capture')">✕</button>
      </div>
      <input id="db-capture-input" type="text" placeholder="Capture a thought, task, or idea..." style="background:var(--background-primary);border:1px solid var(--background-modifier-border);border-radius:4px;padding:8px 10px;margin-bottom:7px;font-size:0.9em;width:100%;box-sizing:border-box;color:var(--text-normal)" onkeydown="if(event.key==='Enter')window._dbCapture()"/>
      <button style="background:var(--db-accent);border:none;border-radius:4px;padding:7px;width:100%;font-size:0.9em;font-weight:700;color:#fff;cursor:pointer" onclick="window._dbCapture()">+ Add to Inbox</button>
    </div>`,

  heartbeat: `
    <div class="db-card" data-id="heartbeat">
      <div class="db-card-hd">
        <span class="db-drag-handle">⠿</span>
        <div class="db-label" style="margin-bottom:0;flex:1">STATUS</div>
        <button class="db-dismiss-btn" onclick="window._dbDismissCard('heartbeat')">✕</button>
      </div>
      ${hbHTML}
    </div>`,
};

// ── RENDER HELPERS ────────────────────────────────────────────────────────────
function renderGrid(lyt) {
  const widths = lyt.columnWidths.length === lyt.columns.length
    ? lyt.columnWidths
    : Array(lyt.columns.length).fill("1fr");
  const colsHTML = lyt.columns.map((cardIds, i) => {
    const cards = cardIds
      .filter(id => !lyt.hidden.includes(id) && CARD_HTML[id])
      .map(id => CARD_HTML[id])
      .join("");
    return `<div class="db-col" data-col-idx="${i}">${cards}</div>`;
  }).join("");
  return `<div class="db-grid" id="db-main-grid" style="grid-template-columns:${widths.join(" ")}">${colsHTML}</div>`;
}

// ── RENDER ────────────────────────────────────────────────────────────────────
const root = dv.container;
root.innerHTML = `
<div id="db-header">
  <div id="db-header-locked" style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
    <div>
      <div style="font-size:18px;font-weight:700;color:var(--text-normal);margin-bottom:2px">Second Brain</div>
      <div style="color:var(--text-muted);font-size:0.8em">${dateStr} · Kuala Lumpur</div>
    </div>
    <div style="display:flex;gap:6px;align-items:center;margin-top:2px;flex-shrink:0">
      <button onclick="window._dbRefresh()" style="background:rgba(163,113,247,0.08);border:1px solid rgba(163,113,247,0.25);border-radius:4px;color:#a371f7;font-size:0.7rem;padding:4px 10px;cursor:pointer">↻ Refresh</button>
      <button onclick="window._dbToggleEditMode()" style="background:rgba(163,113,247,0.12);border:1px solid rgba(163,113,247,0.35);border-radius:4px;color:#a371f7;font-size:0.7rem;padding:4px 10px;cursor:pointer">⊞ Edit Layout</button>
    </div>
  </div>
  <div id="db-header-edit" style="display:none;justify-content:space-between;align-items:center;margin-bottom:12px">
    <div>
      <div style="font-size:18px;font-weight:700;color:var(--text-normal);margin-bottom:2px">Second Brain</div>
      <div style="color:#a371f7;font-size:0.75em">Edit mode — drag cards, add/remove columns</div>
    </div>
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
      <button class="db-col-add" onclick="window._dbAddColumn()" style="background:rgba(163,113,247,0.1);border:1px solid rgba(163,113,247,0.3);border-radius:4px;color:#a371f7;font-size:0.7rem;padding:3px 8px;cursor:pointer">+ col</button>
      <button class="db-col-remove" onclick="window._dbRemoveColumn()" style="background:rgba(255,82,82,0.08);border:1px solid rgba(255,82,82,0.3);border-radius:4px;color:#f85149;font-size:0.7rem;padding:3px 8px;cursor:pointer">− col</button>
      <button onclick="window._dbResetLayout()" style="background:transparent;border:1px solid rgba(255,255,255,0.15);border-radius:4px;color:var(--text-muted);font-size:0.7rem;padding:3px 8px;cursor:pointer">Reset Layout</button>
      <button onclick="window._dbLockLayout()" style="background:rgba(163,113,247,0.2);border:1px solid #a371f7;border-radius:4px;color:#a371f7;font-size:0.7rem;padding:3px 9px;cursor:pointer;font-weight:700">✓ Lock Layout</button>
    </div>
  </div>
</div>

${renderGrid(layout)}

<div class="db-card" style="margin-top:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div style="display:flex;align-items:center;gap:8px">
      <button onclick="window._dbNavMonth(-1)" style="background:transparent;border:1px solid var(--background-modifier-border);border-radius:4px;color:var(--text-muted);cursor:pointer;font-size:0.9rem;padding:1px 7px;line-height:1.4">‹</button>
      <div class="db-label" id="db-cal-label" style="margin-bottom:0">${CAL_MONTHS[CAL_START_IDX].label}</div>
      <button onclick="window._dbNavMonth(1)"  style="background:transparent;border:1px solid var(--background-modifier-border);border-radius:4px;color:var(--text-muted);cursor:pointer;font-size:0.9rem;padding:1px 7px;line-height:1.4">›</button>
    </div>
    <span id="db-cal-dlcount" style="color:var(--text-muted);font-size:0.65rem">${CAL_MONTHS[CAL_START_IDX].dls.length} deadline${CAL_MONTHS[CAL_START_IDX].dls.length===1?"":"s"} this month</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1.2fr;gap:16px">
    <div>
      ${CAL_MONTHS.map((cm,i)=>`<div id="db-cal-grid-${i}" style="display:${i===CAL_START_IDX?"block":"none"}">${cm.grid}</div>`).join("")}
    </div>
    <div style="border-left:1px solid var(--background-modifier-border);padding-left:16px">
      <div class="db-label" style="margin-bottom:6px">DEADLINES</div>
      <div id="db-cal-dllist">${makeDlList(CAL_MONTHS[CAL_START_IDX].dls)}</div>
    </div>
  </div>
</div>
`;

window._dbOpenNote = (path) => app.workspace.openLinkText(path, "", false);

function _dbForceRefresh() {
  const view = app.workspace.activeLeaf?.view;
  if (view?.previewMode) {
    view.previewMode.rerender(true);
  } else {
    const dvp = app.plugins.plugins["dataview"];
    if (dvp?.index) dvp.index.revision = (dvp.index.revision ?? 0) + 1;
    app.metadataCache.trigger("dataview:refresh-views");
  }
}

window._dbRefresh = async function() {
  const btn = document.querySelector('button[onclick="window._dbRefresh()"]');
  if (btn) btn.textContent = "↻ Refreshing…";

  const cp = window.require?.('child_process');
  if (cp) {
    const parts = app.vault.adapter.basePath.replace(/\\/g, '/').split('/');
    const projectDir = parts.slice(0, -2).join('\\').replace(/\//g, '\\');
    const scriptPath = projectDir + '\\.claude\\scripts\\refresh.py';
    await new Promise((resolve) => {
      cp.exec(
        `py "${scriptPath}"`,
        { cwd: projectDir, env: { ...process.env, CLAUDE_PROJECT_DIR: projectDir }, windowsHide: true },
        (err, stdout, stderr) => {
          if (err) new Notice('Refresh failed: ' + (stderr || err.message), 5000);
          resolve();
        }
      );
    });
  } else {
    new Notice('child_process unavailable — run: py .claude/scripts/refresh.py', 5000);
  }

  _dbForceRefresh();
};


window._dbCalIdx = CAL_START_IDX;
window._dbNavMonth = (delta) => {
  const next = Math.max(0, Math.min(CAL_MONTHS.length - 1, window._dbCalIdx + delta));
  if (next === window._dbCalIdx) return;
  root.querySelector(`#db-cal-grid-${window._dbCalIdx}`).style.display = "none";
  root.querySelector(`#db-cal-grid-${next}`).style.display = "block";
  root.querySelector("#db-cal-label").textContent = CAL_MONTHS[next].label;
  const dls = CAL_MONTHS[next].dls;
  root.querySelector("#db-cal-dlcount").textContent = `${dls.length} deadline${dls.length===1?"":"s"} this month`;
  root.querySelector("#db-cal-dllist").innerHTML = makeDlList(dls);
  window._dbCalIdx = next;
};

window._dbOpenDay = async (k) => {
  const path = `daily/${k}.md`;
  let exists = true;
  try { await app.vault.adapter.stat(path); } catch { exists = false; }
  if (!exists) await app.vault.adapter.write(path, `# ${k}\n`);
  app.workspace.openLinkText(path, "", false);
};

window._dbShowDlDay = (k) => {
  const dls = dlMap[k] || [];
  if (!dls.length) return;
  const d = new Date(k+"T00:00:00");
  const label = d.toLocaleDateString("en-MY",{weekday:"short",day:"numeric",month:"short"});
  new Notice(`${label}\n\n${dls.map(x=>`📌 ${x.title}  —  ${x.course}`).join("\n")}`, 6000);
};

window._dbCapture = async () => {
  const inputEl = root.querySelector("#db-capture-input");
  const input = inputEl?.value?.trim();
  if (!input) return;
  const path = `daily/${todayStr}.md`;
  let existing = "";
  try { existing = await app.vault.adapter.read(path); } catch {}
  const content = existing ? existing + `\n- ${input}` : `# ${todayStr}\n\n- ${input}`;
  await app.vault.adapter.write(path, content);
  if (inputEl) inputEl.value = "";
  new Notice("Captured to " + path);
};

window._dbToggleEditMode = function() {
  window.__dbEditMode = !window.__dbEditMode;
  const grid   = root.querySelector("#db-main-grid");
  const locked = root.querySelector("#db-header-locked");
  const edit   = root.querySelector("#db-header-edit");
  const addBtn = root.querySelector(".db-col-add");
  const remBtn = root.querySelector(".db-col-remove");

  if (window.__dbEditMode) {
    grid.classList.add("db-edit-mode");
    locked.style.display = "none";
    edit.style.display   = "flex";
    if (addBtn) addBtn.disabled = window.__dbLayout.columns.length >= 4;
    if (remBtn) remBtn.disabled = window.__dbLayout.columns.length <= 1;
  } else {
    grid.classList.remove("db-edit-mode");
    locked.style.display = "flex";
    edit.style.display   = "none";
  }
};

// ── SORTABLE ──────────────────────────────────────────────────────────────────
if (!window.Sortable) {
  try {
    const code = await app.vault.adapter.read(".obsidian/scripts/sortable.min.js");
    const script = document.createElement("script");
    script.textContent = code;
    document.head.appendChild(script);
  } catch {
    new Notice("dashboard: sortable.min.js not found — drag-and-drop disabled");
  }
}

function initSortable() {
  if (!window.Sortable) return;
  const grid = root.querySelector("#db-main-grid");
  if (!grid) return;
  grid.querySelectorAll(".db-col").forEach(col => {
    new Sortable(col, {
      group:       "cards",
      animation:   150,
      handle:      ".db-drag-handle",
      ghostClass:  "db-drag-ghost",
    });
  });
}
initSortable();

window._dbLockLayout = async function() {
  const grid = root.querySelector("#db-main-grid");
  const cols = [...grid.querySelectorAll(".db-col")];
  window.__dbLayout.columns = cols.map(col =>
    [...col.querySelectorAll(".db-card[data-id]")].map(el => el.getAttribute("data-id"))
  );
  if (window.__dbLayout.columnWidths.length !== cols.length) {
    window.__dbLayout.columnWidths = Array(cols.length).fill("1fr");
  }
  await app.vault.adapter.write(
    "state/dashboard-layout.json",
    JSON.stringify(window.__dbLayout, null, 2)
  );
  window._dbToggleEditMode();
  new Notice("Layout saved");
};

window._dbResetLayout = async function() {
  try { await app.vault.adapter.remove("state/dashboard-layout.json"); } catch {}
  _dbForceRefresh();
};

window._dbAddColumn = function() {
  if (window.__dbLayout.columns.length >= 4) return;
  window.__dbLayout.columns.push([]);
  window.__dbLayout.columnWidths = Array(window.__dbLayout.columns.length).fill("1fr");

  const grid    = root.querySelector("#db-main-grid");
  const newCol  = document.createElement("div");
  newCol.className = "db-col";
  newCol.setAttribute("data-col-idx", String(window.__dbLayout.columns.length - 1));
  grid.appendChild(newCol);
  grid.style.gridTemplateColumns = window.__dbLayout.columnWidths.join(" ");

  const addBtn = root.querySelector(".db-col-add");
  const remBtn = root.querySelector(".db-col-remove");
  if (addBtn) addBtn.disabled = window.__dbLayout.columns.length >= 4;
  if (remBtn) remBtn.disabled = false;

  if (window.Sortable) {
    new Sortable(newCol, { group:"cards", animation:150, handle:".db-drag-handle", ghostClass:"db-drag-ghost" });
  }
};

window._dbRemoveColumn = function() {
  if (window.__dbLayout.columns.length <= 1) return;
  const grid    = root.querySelector("#db-main-grid");
  const cols    = [...grid.querySelectorAll(".db-col")];
  const lastCol = cols[cols.length - 1];
  const prevCol = cols[cols.length - 2];

  // Move cards to the previous column (DOM) and read their ids before moving
  const removedIds = [...lastCol.querySelectorAll(".db-card[data-id]")].map(el => el.getAttribute("data-id"));
  [...lastCol.querySelectorAll(".db-card")].forEach(card => prevCol.appendChild(card));

  // Update in-memory layout using DOM-derived ids
  window.__dbLayout.columns.pop();
  window.__dbLayout.columns[window.__dbLayout.columns.length - 1].push(...removedIds);
  window.__dbLayout.columnWidths = Array(window.__dbLayout.columns.length).fill("1fr");

  lastCol.remove();
  grid.style.gridTemplateColumns = window.__dbLayout.columnWidths.join(" ");

  const addBtn = root.querySelector(".db-col-add");
  const remBtn = root.querySelector(".db-col-remove");
  if (addBtn) addBtn.disabled = false;
  if (remBtn) remBtn.disabled = window.__dbLayout.columns.length <= 1;
};

window._dbDismissCard = function(id) {
  const card = document.querySelector(`.db-card[data-id="${id}"]`);
  if (card) card.remove();
  if (!window.__dbLayout.hidden.includes(id)) {
    window.__dbLayout.hidden.push(id);
  }
};
```

