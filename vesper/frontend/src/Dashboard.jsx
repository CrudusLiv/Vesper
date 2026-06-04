import { useRef } from 'react'
import { useStore } from './state/store.jsx'
import { useVesper } from './hooks/useVesper.js'
import { useCapture } from './hooks/useCapture.js'
import StatusBar from './components/StatusBar.jsx'
import LeftDock from './components/LeftDock.jsx'
import VoiceOrb from './components/VoiceOrb.jsx'
import ChatPanel from './components/ChatPanel.jsx'

export default function Dashboard() {
  const { state } = useStore()
  const { sendChat, search, startVoice, stopVoice, sttSupported } = useVesper()
  const cap = useCapture()
  const debounce = useRef(null)

  function onSearch(q) {
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => search(q), 300)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <StatusBar status={state.status} />
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <div style={{ flex: '0 0 23%' }}>
          <LeftDock memoryResults={state.memory.results} onSearch={onSearch} cap={cap} />
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <VoiceOrb state={state.orb} />
        </div>
        <div style={{ flex: '0 0 34%' }}>
          <ChatPanel
            messages={state.chat.messages}
            pending={state.chat.pending}
            onSend={sendChat}
            voiceSupported={sttSupported}
            listening={state.orb === 'listening'}
            onMic={() => (state.orb === 'listening' ? stopVoice() : startVoice())}
          />
        </div>
      </div>
    </div>
  )
}
