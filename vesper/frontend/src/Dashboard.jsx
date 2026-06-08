import { useState, useRef, useEffect } from 'react'
import { useStore } from './state/store.jsx'
import { useVesper } from './hooks/useVesper.js'
import { useCapture } from './hooks/useCapture.js'
import StatusBar from './components/StatusBar.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import { ActivePanel } from './components/ActivePanel.jsx'
import { ParticleOrb } from './components/ParticleOrb.jsx'
import LeftDock from './components/LeftDock.jsx'
import './Dashboard.css'

const SIDEBAR_MIN = 160
const SIDEBAR_MAX = 400
const SIDEBAR_DEFAULT = 220
const STORAGE_KEY = 'left-dock-width'

export default function Dashboard() {
  const { state } = useStore()
  const { sendChat, search, startVoice, stopVoice, sttSupported } = useVesper()
  const cap = useCapture()
  const debounce = useRef(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? parseInt(saved, 10) : SIDEBAR_DEFAULT
  })
  const [isResizing, setIsResizing] = useState(false)
  const [minimizedPanels, setMinimizedPanels] = useState([])

  useEffect(() => {
    return () => clearTimeout(debounce.current)
  }, [])

  useEffect(() => {
    if (!isResizing) return
    function onMove(e) {
      setSidebarWidth(Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, e.clientX)))
    }
    function onUp() {
      setIsResizing(false)
      setSidebarWidth(w => {
        localStorage.setItem(STORAGE_KEY, String(w))
        return w
      })
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [isResizing])

  function onSearch(q) {
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => search(q), 300)
  }

  function handleMinimize(panel) {
    setMinimizedPanels(prev => {
      if (prev.some(p => p.id === panel.id)) return prev
      return [...prev, panel]
    })
  }

  function handleRestore(panelId) {
    setMinimizedPanels(prev => prev.filter(p => p.id !== panelId))
  }

  const activePanelMinimized = minimizedPanels.some(p => p.id === 'active-panel')

  return (
    <div className="dashboard" data-resizing={isResizing || undefined}>
      <div className="dashboard-sidebar" style={{ width: sidebarWidth + 'px' }}>
        <LeftDock
          memoryResults={state.memory.results}
          onSearch={onSearch}
          cap={cap}
          onResizeStart={() => setIsResizing(true)}
          minimizedPanels={minimizedPanels}
          onRestorePanel={handleRestore}
        />
      </div>

      <div className="dashboard-center">
        <ParticleOrb state={state.orb} />
      </div>

      <StatusBar status={state.status} />
      {settingsOpen && <SettingsPanel />}

      {!activePanelMinimized && (
        <ActivePanel
          memoryResults={state.memory.results}
          onSearch={onSearch}
          messages={state.chat.messages}
          pending={state.chat.pending}
          onSend={sendChat}
          voiceSupported={sttSupported}
          listening={state.orb === 'listening'}
          onMic={() => (state.orb === 'listening' ? stopVoice() : startVoice())}
          onMinimize={handleMinimize}
        />
      )}

      <button
        className="gear-btn"
        onClick={() => setSettingsOpen(o => !o)}
        aria-label="Toggle settings"
      >
        ⚙
      </button>
    </div>
  )
}
