---
cssclasses: [dashboard]
---

# Second Brain — Home

## Finance Pulse

```dataviewjs
const now = new Date();
const month = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
const raw = await dv.io.load(`finance/${month}.md`);
if (!raw) { dv.paragraph(`_No finance data for ${month}._`); return; }

const totalMatch = raw.match(/\[!summary\]\s*RM\s*([\d,.]+)/);
const total = totalMatch ? totalMatch[1] : "?";
const totalNum = parseFloat(total.replace(",", "")) || 0;

const BUDGET = 1500;
const pct = Math.min(100, Math.round((totalNum / BUDGET) * 100));
const filled = Math.round(pct / 5);
const bar = "█".repeat(filled) + "░".repeat(20 - filled);

dv.header(4, "Finance Pulse");
dv.paragraph(`**RM ${total}** / RM ${BUDGET} budget`);
dv.paragraph(`\`${bar}\` ${pct}%`);

const catRows = [];
const catRegex = /\|\s+`(\w+)`\s+\|\s+RM\s+([\d,.]+)\s+\|\s+([\d.]+)%/g;
let m;
while ((m = catRegex.exec(raw)) !== null) {
  catRows.push([m[1], `RM ${m[2]}`, `${m[3]}%`]);
}
if (catRows.length) dv.table(["Category", "Amount", "Share"], catRows);
```

## Habits — Daily Pillars

```dataviewjs
const raw = await dv.io.load("HABITS.md");
const isPaused = raw && raw.includes("Stub — paused");

dv.header(4, "Habits — Daily Pillars");
if (isPaused) {
  dv.paragraph("> **Paused** — resumes when uni starts (June 2026).");
  return;
}

const tasks = dv.page("HABITS").file.tasks;
for (const t of tasks.values) {
  const icon = t.completed ? "✅" : "⬜";
  dv.paragraph(`${icon} ${t.text}`);
}
```

## Inbox

```dataviewjs
const discord = dv.page("state/discord-recent");
const github = dv.page("state/github-counts");
const inboxCount = dv.pages('"inbox"')
  .where(p => !p.file.path.includes("_processed") && !p.file.name.startsWith("."))
  .length;

dv.header(4, "Inbox");
dv.paragraph(`**Discord DMs:** ${discord?.unread_dms ?? "_not synced_"}`);
dv.paragraph(`**GitHub pushes:** ${github?.prs_open ?? "_not synced_"}`);
dv.paragraph(`**Vault inbox:** ${inboxCount} file(s)`);

if (discord) {
  const dmRaw = await dv.io.load("state/discord-recent.md");
  const body = dmRaw ? dmRaw.replace(/^---[\s\S]*?---\n/, "").trim() : "";
  if (body) dv.paragraph(body);
}
```
