import { useState } from 'react'
import { useFeed } from '../hooks/useFeed.js'
import MemoryPanel from './MemoryPanel.jsx'
import FinancePanel from './FinancePanel.jsx'
import NotesPanel from './NotesPanel.jsx'
import SchedulePanel from './SchedulePanel.jsx'
import VaultBrowser from './VaultBrowser.jsx'
import UploadPanel from './UploadPanel.jsx'
import FeedPanel from './FeedPanel.jsx'
import './LeftDock.css'

const TABS = [
  { id: 'Memory',   icon: '🧠' },
  { id: 'Finance',  icon: '💰' },
  { id: 'Notes',    icon: '📝' },
  { id: 'Schedule', icon: '📅' },
  { id: 'Files',    icon: '📁' },
  { id: 'Uploads',  icon: '⬆' },
  { id: 'Alerts',   icon: '🔔' },
]

export default function LeftDock({ memoryResults, onSearch, cap, onResizeStart, minimizedPanels = [], onRestorePanel }) {
  const [tab, setTab] = useState(() => localStorage.getItem('left-dock-tab') || 'Memory')
  const { items: feedItems, unreadCount, markRead } = useFeed()
  return (
    <div className="left-dock">
      <nav className="left-dock-nav" role="tablist">
        {TABS.map(({ id, icon }) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => { setTab(id); localStorage.setItem('left-dock-tab', id) }}
            className="left-dock-tab"
          >
            <span className="left-dock-tab-icon" aria-hidden="true">{icon}</span>
            <span className="left-dock-tab-label">{id}</span>
            {id === 'Alerts' && unreadCount > 0 && (
              <span className="left-dock-badge">{unreadCount}</span>
            )}
          </button>
        ))}
      </nav>
      <div className="left-dock-content">
        {tab === 'Memory'   && <MemoryPanel results={memoryResults} onSearch={onSearch} />}
        {tab === 'Finance'  && <FinancePanel onLog={cap.logFinance} onLoadSummary={cap.loadFinanceSummary} />}
        {tab === 'Notes'    && <NotesPanel onSave={cap.saveNote} />}
        {tab === 'Schedule' && <SchedulePanel onLoad={cap.getSchedule} onSave={cap.saveSchedule} />}
        {tab === 'Files'    && <VaultBrowser onList={cap.listVault} onDelete={cap.deleteVaultFile} onUndo={cap.undoVault} />}
        {tab === 'Uploads'  && <UploadPanel onUpload={cap.uploadDocument} onListUploads={cap.listUploads} />}
        {tab === 'Alerts'   && <FeedPanel items={feedItems} markRead={markRead} />}
      </div>
      {minimizedPanels.length > 0 && (
        <div className="left-dock-minimized">
          <span className="left-dock-minimized-label">Panels</span>
          {minimizedPanels.map(panel => (
            <button
              key={panel.id}
              className="left-dock-minimized-btn"
              onClick={() => onRestorePanel(panel.id)}
              title={`Restore ${panel.title}`}
            >
              <span className="left-dock-minimized-icon">{panel.icon}</span>
              <span>{panel.title}</span>
            </button>
          ))}
        </div>
      )}
      <div className="left-dock-resizer" onMouseDown={onResizeStart} />
    </div>
  )
}
