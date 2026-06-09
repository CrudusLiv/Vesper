import { useState } from 'react';
import { FloatingPanel } from './FloatingPanel.jsx';
import MemoryPanel from './MemoryPanel.jsx';
import CommandCenter from './CommandCenter.jsx';
import './ActivePanel.css';

export function ActivePanel({
  memoryResults,
  onSearch,
  onMinimize,
}) {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <FloatingPanel
      panelId="active-panel"
      title="Vesper"
      icon="💬"
      defaultPosition={() => ({ x: Math.max(20, window.innerWidth - 420), y: 20 })}
      onMinimize={onMinimize}
    >
      <div className="active-panel-wrapper">
        <div className="tab-bar" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === 'chat'}
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'search'}
            className={`tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            Search
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'chat' && <CommandCenter />}
          {activeTab === 'search' && (
            <MemoryPanel results={memoryResults} onSearch={onSearch} />
          )}
        </div>
      </div>
    </FloatingPanel>
  );
}
