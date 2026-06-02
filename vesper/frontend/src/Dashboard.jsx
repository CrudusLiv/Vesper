import { useRef } from 'react'
import { useStore } from './state/store.jsx'
import { useJarvis } from './hooks/useJarvis.js'
import StatusBar from './components/StatusBar.jsx'
import MemoryPanel from './components/MemoryPanel.jsx'
import VoiceOrb from './components/VoiceOrb.jsx'
import ChatPanel from './components/ChatPanel.jsx'

export default function Dashboard() {
  const { state } = useStore()
  const { sendChat, search } = useJarvis()
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
          <MemoryPanel results={state.memory.results} onSearch={onSearch} />
        </div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <VoiceOrb state={state.orb} />
        </div>
        <div style={{ flex: '0 0 34%' }}>
          <ChatPanel messages={state.chat.messages} pending={state.chat.pending} onSend={sendChat} />
        </div>
      </div>
    </div>
  )
}
