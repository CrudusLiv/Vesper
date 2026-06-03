import { useState } from 'react'
import MemoryPanel from './MemoryPanel.jsx'
import FinancePanel from './FinancePanel.jsx'
import NotesPanel from './NotesPanel.jsx'
import SchedulePanel from './SchedulePanel.jsx'
import VaultBrowser from './VaultBrowser.jsx'

const TABS = ['Memory', 'Finance', 'Notes', 'Schedule', 'Files']

export default function LeftDock({ memoryResults, onSearch, cap }) {
  const [tab, setTab] = useState('Memory')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', borderRight: '1px solid var(--line)', background: 'rgba(13,17,23,0.5)' }}>
      <div role="tablist" style={{ display: 'flex', flexWrap: 'wrap', gap: 4, padding: 6, borderBottom: '1px solid var(--line)' }}>
        {TABS.map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            style={{ fontSize: 10, padding: '3px 7px', borderRadius: 5, cursor: 'pointer',
              border: `1px solid ${tab === t ? 'var(--accent)' : 'var(--line)'}`,
              background: tab === t ? 'var(--accent)' : 'transparent',
              color: tab === t ? '#fff' : 'var(--dim)' }}
          >
            {t}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {tab === 'Memory' && <MemoryPanel results={memoryResults} onSearch={onSearch} />}
        {tab === 'Finance' && <FinancePanel onLog={cap.logFinance} onLoadSummary={cap.loadFinanceSummary} />}
        {tab === 'Notes' && <NotesPanel onSave={cap.saveNote} />}
        {tab === 'Schedule' && <SchedulePanel onLoad={cap.getSchedule} onSave={cap.saveSchedule} />}
        {tab === 'Files' && <VaultBrowser onList={cap.listVault} onDelete={cap.deleteVaultFile} onUndo={cap.undoVault} />}
      </div>
    </div>
  )
}
