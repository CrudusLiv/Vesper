---
cssclasses:
  - dashboard
---

```dataviewjs
const now      = new Date();
const monthKey = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
const monthLabel = now.toLocaleDateString("en-MY",{month:"long",year:"numeric"}).toUpperCase();
const todayStr = now.toISOString().slice(0,10);
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

let focusTitle = "No active focus", focusSubtitle = "", focusMilestone = "", focusNext = "", focusColor = "var(--text-muted)";
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
const allTasks = dv.pages().file.tasks.where(t => !t.completed);
const topTasks = [...allTasks.sort(t => t.due?.ts ?? Number.MAX_SAFE_INTEGER, "asc")].slice(0, 5);
function dotColor(t) {
  if (!t.due) return "#a371f7";
  const diff = (t.due.ts - now.getTime()) / 864e5;
  return diff < 0 ? "#f85149" : diff < 1 ? "#d29922" : "#a371f7";
}
const taskRows = topTasks.map(t =>
  `<div style="display:flex;align-items:center;gap:7px;background:var(--background-primary);border-radius:4px;padding:5px 8px">` +
  `<div style="width:5px;height:5px;border-radius:50%;background:${dotColor(t)};flex-shrink:0"></div>` +
  `<span style="font-size:0.8em">${String(t.text).replace(/\[.*?\]/g,"").trim()}</span></div>`
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
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px">
      <span></span>
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
if (hbRaw) {
  try {
    if (JSON.parse(hbRaw).timestamp) {
      const nowMins = now.getHours() * 60 + now.getMinutes();
      for (let h = 9; h <= 21; h++) for (const min of [0, 30]) {
        const tMins = h * 60 + min;
        if (tMins >= nowMins - 120 && tMins <= nowMins + 120)
          events.push({time:`${String(h).padStart(2,"0")}:${String(min).padStart(2,"0")}`, title:"Heartbeat tick", subtitle:"Automated"});
      }
    }
  } catch {}
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

// ── RENDER ────────────────────────────────────────────────────────────────────
const root = dv.el("div", "", {cls: "dashboard"});
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
      <div class="db-label">VAULT GRAPH</div>
      <div class="db-graph"></div>
    </div>

    <div class="db-card">
      <div class="db-label">QUICK CAPTURE</div>
      <div style="background:var(--background-primary);border-radius:4px;padding:6px 8px;margin-bottom:6px;font-size:0.8em;color:var(--text-muted);font-style:italic">Capture a thought, task, or idea...</div>
      <button class="db-capture-btn" style="background:var(--db-accent);border:none;border-radius:4px;padding:5px;width:100%;font-size:0.8em;font-weight:700;color:#fff;cursor:pointer">+ Add to Inbox</button>
    </div>

    <div class="db-card">
      <div class="db-label">HEARTBEAT</div>
      ${hbHTML}
    </div>

  </div>

</div>
`;

root.querySelector(".db-capture-btn")?.addEventListener("click", async () => {
  const input = window.prompt("Capture a thought, task, or idea:");
  if (!input || !input.trim()) return;
  const path = `daily/${todayStr}.md`;
  let existing = "";
  try { existing = await app.vault.adapter.read(path); } catch {}
  const content = existing ? existing + `\n- ${input.trim()}` : `# ${todayStr}\n\n- ${input.trim()}`;
  await app.vault.adapter.write(path, content);
  new Notice("Captured to " + path);
});
```

```juggl
CURRENT
height: 120px
```
