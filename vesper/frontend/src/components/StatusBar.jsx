import { FloatingPanel } from './FloatingPanel.jsx';
import './StatusBar.css';

export default function StatusBar({ status }) {
  if (!status || Object.keys(status.integrations).length === 0) {
    return null;
  }

  const integrations = status.integrations;

  return (
    <FloatingPanel panelId="status-bar" title="System" defaultPosition={{ x: 230, y: 20 }}>
      <div className="status-grid">
        {Object.entries(integrations).map(([name, info]) => (
          <div key={name} className="status-item">
            <div className="status-icon" data-ready={info.ready}>
              ●
            </div>
            <div className="status-label">{name}</div>
            {info.missing && info.missing.length > 0 && (
              <div className="status-missing" title={info.missing.join(', ')}>
                {info.missing.length} missing
              </div>
            )}
          </div>
        ))}
      </div>
    </FloatingPanel>
  );
}
