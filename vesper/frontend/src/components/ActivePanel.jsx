import { useState } from 'react';
import { FloatingPanel } from './FloatingPanel.jsx';
import MemoryPanel from './MemoryPanel.jsx';
import ChatPanel from './ChatPanel.jsx';
import './ActivePanel.css';

export function ActivePanel({
  memoryResults,
  onSearch,
  messages,
  pending,
  onSend,
  voiceSupported,
  listening,
  onMic,
}) {
  const [activeTab, setActiveTab] = useState('search');

  return (
    <FloatingPanel panelId="active-panel" title="Info" defaultPosition={{ x: 'calc(100% - 420px)', y: 20 }}>
      <div className="active-panel-wrapper">
        <div className="tab-bar">
          <button
            className={`tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            Search
          </button>
          <button
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'search' && (
            <MemoryPanel results={memoryResults} onSearch={onSearch} />
          )}
          {activeTab === 'chat' && (
            <ChatPanel
              messages={messages}
              pending={pending}
              onSend={onSend}
              voiceSupported={voiceSupported}
              listening={listening}
              onMic={onMic}
            />
          )}
        </div>
      </div>
    </FloatingPanel>
  );
}
