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
const [dlRaw, projRaw, gcalRaw, hbRaw, habitsRaw, finRaw] = await Promise.all([
  dv.io.load("DEADLINES.md"),
  dv.io.load("PROJECTS.md"),
  dv.io.load("state/gcal-today.md"),
  dv.io.load("state/heartbeat-state.json"),
  dv.io.load("HABITS.md"),
  dv.io.load(`finance/${monthKey}.md`),
]);

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
  `<div style="display:flex;align-items:center;gap:7px;background:var(--background-primary);border-radius:4px;padding:5px 8px;cursor:pointer" onclick="window._dbOpenNote('${t.path}')">` +
  `<div style="width:5px;height:5px;border-radius:50%;background:${dotColor(t)};flex-shrink:0"></div>` +
  `<span style="font-size:0.8em">${cleanText(t.text)}</span></div>`
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
      <span style="font-weight:700;font-size:11px">RM ${total.toLocaleString()} <span style="color:var(--text-muted);font-weight:400;font-size:0.65rem">/ ${BUDGET}</span></span>
    </div>
    <div style="background:var(--background-modifier-border);height:4px;border-radius:2px;margin-bottom:9px">
      <div class="db-bar-fill" style="width:${pct}%;height:100%"></div>
    </div>
    ${catRows.map(c =>
      `<div style="margin-bottom:5px">` +
      `<div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-bottom:2px"><span>${c.name}</span><span style="color:var(--db-accent)">RM ${c.amt.toLocaleString()} · ${c.pct}%</span></div>` +
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
    `<div><div style="font-size:0.8em${isNow?";font-weight:600":""}">${ev.title}</div>` +
    `<div style="font-size:0.7rem;color:${isNow?"var(--db-accent)":"var(--text-muted)"}">${ev.subtitle}</div></div></div>`;
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
        `<span style="color:var(--text-muted);font-size:0.7rem;flex-shrink:0;margin-left:8px">${when}</span></div>`;
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
    : [...ht].map(t => `<div style="display:flex;align-items:center;gap:6px;font-size:0.8em;margin-bottom:4px"><span>${t.completed?"✅":"◻"}</span><span>${String(t.text)}</span></div>`).join("");
}

// ── HEARTBEAT ─────────────────────────────────────────────────────────────────
let hbHTML = "";
if (!hbRaw) {
  hbHTML = `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No heartbeat data yet</div>`;
} else {
  let hs = null;
  try { hs = JSON.parse(hbRaw); } catch { hbHTML = `<div style="color:#f85149;font-size:0.85em">Corrupt state file</div>`; }
  if (hs) {
    const lastTs  = hs.timestamp ? new Date(hs.timestamp * 1000) : null;
    const mAgo    = lastTs ? Math.round((now - lastTs) / 6e4) : null;
    const nextTs  = lastTs ? new Date(lastTs.getTime() + 30 * 6e4) : null;
    const mUntil  = nextTs ? Math.round((nextTs - now) / 6e4) : null;
    const barPct  = Math.round(Math.min(30, mAgo ?? 0) / 30 * 100);
    const intRows = [
      {key:"discord", label:"discord", detail:hs.discord?.error ?? `${hs.discord?.new_count??0} msgs`},
      {key:"github",  label:"github",  detail:hs.github?.error  ?? `${hs.github?.push_count??0} pushes`},
      {key:"inbox",   label:"inbox",   detail:hs.inbox?.error   ?? `${hs.inbox?.count??0} files`},
    ].map(r => {
      const ok = !hs[r.key]?.error;
      return `<div style="display:flex;justify-content:space-between;font-size:0.7rem"><span>${ok?"🟢":"🔴"} ${r.label}</span><span style="color:${ok?"#3fb950":"#f85149"}">${r.detail}</span></div>`;
    }).join("");
    hbHTML = `
      <div style="background:var(--background-primary);border-radius:4px;padding:6px 8px;margin-bottom:7px">
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-bottom:3px">
          <span style="color:var(--text-muted)">Last</span>
          <span>${lastTs ? `${lastTs.toLocaleTimeString("en-MY",{hour:"2-digit",minute:"2-digit",hour12:false})} (${mAgo}m ago)` : "unknown"}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;margin-bottom:4px">
          <span style="color:var(--text-muted)">Next</span>
          <span style="color:var(--db-accent)">${nextTs ? `${nextTs.toLocaleTimeString("en-MY",{hour:"2-digit",minute:"2-digit",hour12:false})} (in ${mUntil}m)` : "unknown"}</span>
        </div>
        <div style="background:var(--background-modifier-border);height:2px;border-radius:1px">
          <div style="background:var(--db-accent);width:${barPct}%;height:100%;border-radius:1px"></div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:3px">${intRows}</div>`;
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
      `<span style="color:var(--text-muted);font-size:0.7rem;white-space:nowrap">${d.course}</span>`+
      `<span style="color:${urgColor};font-size:0.7rem;min-width:42px;text-align:right;font-weight:600">${label}</span>`+
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

// ── RENDER ────────────────────────────────────────────────────────────────────
const root = dv.container;
root.innerHTML = `
<div style="font-size:18px;font-weight:700;color:var(--text-normal);margin-bottom:2px">Second Brain</div>
<div style="color:var(--text-muted);font-size:0.8em;margin-bottom:12px">${dateStr} · Kuala Lumpur</div>
<div class="db-grid">

  <div class="db-col">

    <div class="db-focus db-card">
      <div class="db-label" style="color:var(--db-accent)">● CURRENT FOCUS</div>
      <div style="font-weight:700;font-size:15px;line-height:1.2;margin-bottom:4px">${focusTitle}</div>
      <div style="color:${focusColor};font-size:0.85em;margin-bottom:8px">${focusSubtitle}</div>
      <div style="display:flex;gap:6px">
        ${focusMilestone ? `<span style="background:var(--background-primary);border-radius:3px;padding:3px 8px;font-size:0.65rem;color:var(--db-accent);border:1px solid var(--background-modifier-border)">${focusMilestone}</span>` : ""}
        ${focusNext      ? `<span style="background:var(--background-primary);border-radius:3px;padding:3px 8px;font-size:0.65rem;color:var(--text-muted);border:1px solid var(--background-modifier-border)">${focusNext}</span>` : ""}
      </div>
    </div>

    <div class="db-card">
      <div class="db-label">TODAY'S TASKS</div>
      <div style="display:flex;flex-direction:column;gap:5px">
        ${taskRows || `<div style="color:var(--text-muted);font-style:italic;font-size:0.85em">No open tasks</div>`}
      </div>
      <div style="margin-top:6px;color:var(--text-muted);font-size:0.7rem">${allTasks.length} open</div>
    </div>

    <div class="db-card">
      <div class="db-label">INBOX</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px">
        <div class="db-chip" style="padding:8px;text-align:center">
          <div style="color:var(--db-accent);font-size:18px;font-weight:700;line-height:1">${discordDMs}</div>
          <div style="color:var(--text-muted);font-size:0.6rem;margin-top:3px">Discord DMs</div>
        </div>
        <div class="db-chip" style="padding:8px;text-align:center">
          <div style="color:var(--db-accent);font-size:18px;font-weight:700;line-height:1">${githubPRs}</div>
          <div style="color:var(--text-muted);font-size:0.6rem;margin-top:3px">GitHub</div>
        </div>
        <div class="db-chip" style="padding:8px;text-align:center">
          <div style="color:var(--db-accent);font-size:18px;font-weight:700;line-height:1">${vaultInbox}</div>
          <div style="color:var(--text-muted);font-size:0.6rem;margin-top:3px">Vault inbox</div>
        </div>
      </div>
    </div>

    <div class="db-card">
      <div class="db-label">FINANCE — ${monthLabel}</div>
      ${finHTML}
    </div>


  </div>

  <div class="db-col">

    <div class="db-card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div class="db-label" style="margin-bottom:0">TODAY'S SCHEDULE</div>
        <div style="color:var(--db-accent);font-size:0.65rem">${now.toLocaleDateString("en-MY",{day:"numeric",month:"short"})}</div>
      </div>
      ${schedRows}
      ${gcalNote}
    </div>

    <div class="db-card">
      <div class="db-label">DAILY PILLARS</div>
      ${pillarsHTML}
    </div>

    <div class="db-card">
      <div class="db-label">RECENT NOTES</div>
      ${recentHTML}
    </div>

    <div class="db-card">
      <div class="db-label">QUICK CAPTURE</div>
      <input id="db-capture-input" type="text" placeholder="Capture a thought, task, or idea..." style="background:var(--background-primary);border:1px solid var(--background-modifier-border);border-radius:4px;padding:6px 8px;margin-bottom:6px;font-size:0.8em;width:100%;box-sizing:border-box;color:var(--text-normal)" onkeydown="if(event.key==='Enter')window._dbCapture()"/>
      <button style="background:var(--db-accent);border:none;border-radius:4px;padding:5px;width:100%;font-size:0.8em;font-weight:700;color:#fff;cursor:pointer" onclick="window._dbCapture()">+ Add to Inbox</button>
    </div>

    <div class="db-card">
      <div class="db-label">HEARTBEAT</div>
      ${hbHTML}
    </div>

  </div>

</div>

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
```

