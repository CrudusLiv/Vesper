import { useEffect, useState } from 'react'
import { FloatingPanel } from './FloatingPanel.jsx'
import { useSettings } from '../hooks/useSettings.js'
import './SettingsPanel.css'

export default function SettingsPanel({ onMinimize }) {
  const { settings, loading, error, load, save } = useSettings()
  const [formData, setFormData] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (settings) {
      setFormData(settings)
      setSaveError(null)
    }
  }, [settings])

  const handleChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }))
  }

  const handleFeatureToggle = (feature) => {
    setFormData(prev => ({
      ...prev,
      features: { ...prev.features, [feature]: !prev.features[feature] }
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      await save(formData)
    } catch (err) {
      setSaveError(err.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setFormData(settings)
    setSaveError(null)
  }

  const hasChanges = JSON.stringify(formData) !== JSON.stringify(settings)

  return (
    <FloatingPanel panelId="settings-panel" title="Settings" icon="⚙" defaultPosition={() => ({ x: Math.max(20, window.innerWidth - 370), y: 80 })} onMinimize={onMinimize}>
      {(!settings || !formData) ? (
        <div className="settings-panel">
          {loading && <div className="settings-loading">Loading…</div>}
          {error && <div className="settings-error">{error}</div>}
        </div>
      ) : (
        <div className="settings-panel">
          <div className="settings-section">
            <h3>Active Hours</h3>
            <label>
              Start
              <input
                type="time"
                value={formData.active_hours_start}
                onChange={(e) => handleChange('active_hours_start', e.target.value)}
              />
            </label>
            <label>
              End
              <input
                type="time"
                value={formData.active_hours_end}
                onChange={(e) => handleChange('active_hours_end', e.target.value)}
              />
            </label>
          </div>

          <div className="settings-section">
            <h3>Heartbeat Interval (minutes)</h3>
            <input
              type="number"
              min="5"
              max="120"
              value={formData.heartbeat_interval_minutes || ''}
              onChange={(e) => handleChange('heartbeat_interval_minutes', e.target.value ? parseInt(e.target.value) : '')}
            />
          </div>

          <div className="settings-section">
            <h3>Features</h3>
            {Object.entries(formData.features || {}).map(([feature, enabled]) => (
              <label key={feature} className="feature-toggle">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={() => handleFeatureToggle(feature)}
                />
                {feature}
              </label>
            ))}
          </div>

          <div className="settings-actions">
            <button onClick={handleSave} disabled={!hasChanges || saving}>
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={handleReset} disabled={!hasChanges}>
              Reset
            </button>
          </div>

          {(error || saveError) && <div className="settings-error">{error || saveError}</div>}
        </div>
      )}
    </FloatingPanel>
  )
}
