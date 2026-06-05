import { useState, useRef, useEffect } from 'react'
import { useStore } from './state/store.jsx'
import { useVesper } from './hooks/useVesper.js'
import { useCapture } from './hooks/useCapture.js'
import StatusBar from './components/StatusBar.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import { ActivePanel } from './components/ActivePanel.jsx'
import { ParticleOrb } from './components/ParticleOrb.jsx'
import './Dashboard.css'

export default function Dashboard() {
  const { state } = useStore()
  const { sendChat, search, startVoice, stopVoice, sttSupported } = useVesper()
  const cap = useCapture()
  const debounce = useRef(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  useEffect(() => {
    return () => clearTimeout(debounce.current)
  }, [])

  function onSearch(q) {
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => search(q), 300)
  }

  return (
    <div className="dashboard">
      <StatusBar status={state.status} />
      {settingsOpen && <SettingsPanel />}

      <div className="dashboard-center">
        <ParticleOrb state={state.orb} />
      </div>

      <ActivePanel
        memoryResults={state.memory.results}
        onSearch={onSearch}
        messages={state.chat.messages}
        pending={state.chat.pending}
        onSend={sendChat}
        voiceSupported={sttSupported}
        listening={state.orb === 'listening'}
        onMic={() => (state.orb === 'listening' ? stopVoice() : startVoice())}
      />

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
