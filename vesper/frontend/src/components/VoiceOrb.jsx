export default function VoiceOrb({ state = 'idle' }) {
  return (
    <div className="orbwrap">
      <div className={`orb orb-${state}`} data-testid="orb">
        <div className="ring r1" />
        <div className="ring r2" />
        <div className="core" />
      </div>
      <div className="orb-state">● {state}</div>
    </div>
  )
}
