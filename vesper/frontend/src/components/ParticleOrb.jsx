import { useEffect, useRef } from 'react'

function rnd(a, b) { return a + Math.random() * (b - a) }
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)) }

const COLS = {
  idle:       { hot: '220,232,245', mid: '150,175,205', cool: '55,75,108' },
  listening:  { hot: '235,246,255', mid: '175,205,228', cool: '65,90,130' },
  speaking:   { hot: '248,252,255', mid: '200,220,240', cool: '80,110,150' },
  processing: { hot: '208,226,248', mid: '145,172,205', cool: '50,70,105' },
}

function buildNodes() {
  const NUM = 260
  return Array.from({ length: NUM }, () => {
    const surf = Math.random() < 0.72
    const r = surf ? rnd(0.82, 1.0) : rnd(0.05, 0.80)
    const phi = Math.acos(2 * Math.random() - 1)
    const theta = rnd(0, Math.PI * 2)
    return {
      x3: Math.sin(phi) * Math.cos(theta) * r,
      y3: Math.sin(phi) * Math.sin(theta) * r,
      z3: Math.cos(phi) * r,
      r3: r, surf,
      size: surf ? rnd(1.2, 3.4) : rnd(0.7, 2.0),
      phase: rnd(0, Math.PI * 2),
      speed: rnd(0.3, 1.3),
      rotOff: rnd(0, Math.PI * 2),
      px: 0, py: 0, z: 0, depth: 0, lp: 0, r3c: r,
    }
  })
}

function rotY(x, y, z, a) {
  return { x: x * Math.cos(a) + z * Math.sin(a), y, z: -x * Math.sin(a) + z * Math.cos(a) }
}
function rotX(x, y, z, a) {
  return { x, y: y * Math.cos(a) - z * Math.sin(a), z: y * Math.sin(a) + z * Math.cos(a) }
}

export function ParticleOrb({ state = 'idle' }) {
  const canvasRef = useRef(null)
  const stateRef = useRef(state)
  const rafRef = useRef(null)
  const nodesRef = useRef([])

  useEffect(() => { stateRef.current = state }, [state])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    let W, H, cx, cy, R, t = 0, lastT = 0

    function resize() {
      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      W = rect.width; H = rect.height
      canvas.width = W * dpr; canvas.height = H * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      cx = W / 2; cy = H / 2
      R = Math.min(W, H) * 0.31
      nodesRef.current = buildNodes()
    }

    function proj(x3, y3, z3) {
      const fov = 2.2, pz = z3 + fov, s = fov / Math.max(pz, 0.1)
      return { px: cx + x3 * s * R, py: cy + y3 * s * R, depth: (z3 + 1) / 2 }
    }

    function darc(r, a0, a1, rgba, lw, dash = []) {
      ctx.save(); ctx.beginPath(); ctx.strokeStyle = rgba; ctx.lineWidth = lw
      ctx.setLineDash(dash); ctx.arc(cx, cy, r, a0, a1); ctx.stroke(); ctx.restore()
    }

    function draw(ts) {
      const dt = Math.min((ts - lastT) / 1000, 0.05); lastT = ts; t += dt
      ctx.clearRect(0, 0, W, H)

      const s = stateRef.current
      const col = COLS[s] || COLS.idle
      const bf = s === 'speaking' ? 7 : s === 'listening' ? 3.5 : s === 'processing' ? 2.5 : 1
      const beat = 0.5 + 0.5 * Math.sin(t * bf)
      const sb = 0.5 + 0.5 * Math.sin(t * 0.6)
      const gRY = t * (s === 'processing' ? 0.55 : 0.18)
      const gRX = Math.sin(t * 0.13) * 0.25
      const nodes = nodesRef.current

      const ag = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 1.6)
      ag.addColorStop(0, `rgba(${col.hot},${0.05 + beat * 0.04})`)
      ag.addColorStop(0.6, `rgba(${col.mid},0.02)`)
      ag.addColorStop(1, 'transparent')
      ctx.fillStyle = ag; ctx.beginPath(); ctx.arc(cx, cy, R * 1.6, 0, Math.PI * 2); ctx.fill()

      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]
        n.lp = 0.5 + 0.5 * Math.sin(t * n.speed + n.phase)
        let r3 = n.r3
        if (n.surf) {
          if (s === 'speaking') r3 += n.lp * 0.11 * beat
          else if (s === 'listening') r3 += n.lp * 0.055 * beat
          else if (s === 'processing') r3 += Math.sin(t * 2 + n.phase) * 0.045
          else r3 += n.lp * 0.022
        }
        n.r3c = r3
        const sc = r3 / n.r3
        let p = rotY(n.x3 * sc, n.y3 * sc, n.z3 * sc, gRY + n.rotOff * 0.05)
        p = rotX(p.x, p.y, p.z, gRX)
        const pr = proj(p.x, p.y, p.z)
        n.px = pr.px; n.py = pr.py; n.depth = pr.depth; n.z = p.z
      }
      nodes.sort((a, b) => a.z - b.z)

      ctx.save()
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i]
        if (!a.surf && a.r3c < 0.5) continue
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j]
          if (!b.surf && b.r3c < 0.5) continue
          const dx = a.px - b.px, dy = a.py - b.py
          const d = Math.sqrt(dx * dx + dy * dy)
          const th = R * 0.3
          if (d < th) {
            const frac = 1 - d / th
            const alpha = frac * frac * Math.min(a.depth, b.depth) * 0.42
            ctx.strokeStyle = `rgba(${col.mid},${alpha})`
            ctx.lineWidth = 0.4 + frac * 0.7
            ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.lineTo(b.px, b.py); ctx.stroke()
          }
        }
      }
      ctx.restore()

      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]
        const d = clamp(n.depth, 0, 1)
        let alpha, gr, nc
        if (n.surf) {
          alpha = clamp(0.28 + d * 0.62 + n.lp * 0.1 + beat * 0.07, 0, 1)
          gr = n.size * (2 + n.lp * 1.4 + beat * 0.9)
          nc = d > 0.65 ? col.hot : d > 0.35 ? col.mid : col.cool
        } else {
          alpha = clamp((0.12 + d * 0.4 + n.lp * 0.1) * clamp(n.r3c * 1.3, 0, 1), 0, 1)
          gr = n.size * (1.4 + n.lp)
          nc = col.hot
        }
        const ng = ctx.createRadialGradient(n.px, n.py, 0, n.px, n.py, gr)
        ng.addColorStop(0, `rgba(${nc},${alpha * 0.5})`)
        ng.addColorStop(1, 'transparent')
        ctx.fillStyle = ng; ctx.beginPath(); ctx.arc(n.px, n.py, gr, 0, Math.PI * 2); ctx.fill()
        ctx.beginPath(); ctx.arc(n.px, n.py, n.size * (0.5 + d * 0.5), 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${nc},${clamp(alpha + 0.2, 0, 1)})`; ctx.fill()
      }

      const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.4)
      cg.addColorStop(0, `rgba(255,255,255,${0.2 + beat * 0.2 + sb * 0.07})`)
      cg.addColorStop(0.35, `rgba(${col.hot},${0.12 + beat * 0.1})`)
      cg.addColorStop(1, 'transparent')
      ctx.fillStyle = cg; ctx.beginPath(); ctx.arc(cx, cy, R * 0.4, 0, Math.PI * 2); ctx.fill()

      const r1 = t * (s === 'processing' ? 1.2 : 0.3)
      const r2 = -t * (s === 'processing' ? 0.85 : 0.18)
      darc(R * 1.18, 0, Math.PI * 2, `rgba(${col.mid},0.1)`, 0.8)
      darc(R * 1.18, r1, r1 + Math.PI * 0.5, `rgba(${col.hot},0.45)`, 1.5)
      darc(R * 1.18, r1 + Math.PI, r1 + Math.PI * 1.38, `rgba(${col.mid},0.28)`, 1)
      darc(R * 1.32, r2, r2 + Math.PI * 0.3, `rgba(${col.hot},0.32)`, 1.2)
      darc(R * 1.32, r2 + Math.PI * 0.5, r2 + Math.PI * 0.9, `rgba(${col.mid},0.16)`, 0.8, [4, 6])

      for (let i = 0; i < 48; i++) {
        const a = (i / 48) * Math.PI * 2, il = i % 6 === 0
        const r0 = R * 1.35 + (il ? 0 : 3), r1e = R * 1.35 + (il ? 9 : 5)
        ctx.save()
        ctx.strokeStyle = `rgba(${col.mid},${il ? 0.48 : 0.14})`
        ctx.lineWidth = il ? 1 : 0.5
        ctx.beginPath()
        ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0)
        ctx.lineTo(cx + Math.cos(a) * r1e, cy + Math.sin(a) * r1e)
        ctx.stroke(); ctx.restore()
      }

      if (s === 'speaking') {
        for (let w = 0; w < 4; w++) {
          const wp = ((t * 0.9 + w * 0.25) % 1)
          darc(R * (1.0 + wp * 0.5), 0, Math.PI * 2, `rgba(${col.hot},${(1 - wp) * 0.26 * beat})`, 1.5 - wp * 1.2)
        }
      }
      if (s === 'listening') {
        for (let w = 0; w < 3; w++) {
          const wp = ((t * 0.7 + w * 0.33) % 1)
          darc(R * (1.5 - wp * 0.5), 0, Math.PI * 2, `rgba(${col.hot},${(1 - wp) * 0.2 * beat})`, 1)
        }
      }

      rafRef.current = requestAnimationFrame(draw)
    }

    resize()
    window.addEventListener('resize', resize)
    rafRef.current = requestAnimationFrame(draw)
    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(rafRef.current)
    }
  }, [])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <canvas
        ref={canvasRef}
        data-testid={`orb-${state}`}
        style={{ display: 'block', width: '100%', height: '100%' }}
      />
      <div style={{
        position: 'absolute',
        bottom: 12,
        left: '50%',
        transform: 'translateX(-50%)',
        fontSize: 11,
        letterSpacing: '0.12em',
        color: 'rgba(220,232,245,0.6)',
        fontFamily: 'monospace',
        userSelect: 'none',
        whiteSpace: 'nowrap',
      }}>
        ● {state.toUpperCase()}
      </div>
    </div>
  )
}
