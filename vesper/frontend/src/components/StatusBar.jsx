export default function StatusBar({ status }) {
  const integrations = status?.integrations ?? {}
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '8px 14px', borderBottom: '1px solid var(--line)', background: 'rgba(15,20,27,0.7)' }}>
      <span style={{ fontWeight: 700, letterSpacing: '0.18em', color: 'var(--accent2)', fontSize: 13 }}>VESPER</span>
      <div className="mono" style={{ display: 'flex', gap: 14, marginLeft: 'auto', fontSize: 11 }}>
        {Object.entries(integrations).map(([name, info]) => (
          <span key={name} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            <span
              data-testid={`led-${name}`}
              data-state={info.ready ? 'on' : 'off'}
              style={{
                width: 8, height: 8, borderRadius: '50%',
                background: info.ready ? 'var(--led-on)' : 'var(--led-off)',
                boxShadow: `0 0 8px ${info.ready ? 'var(--led-on)' : 'var(--led-off)'}`,
              }}
            />
            {name}
          </span>
        ))}
      </div>
    </div>
  )
}
