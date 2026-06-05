import { useEffect, useRef } from 'react';
import './ParticleOrb.css';

const PARTICLE_COUNT = 180;
const ORBS_SIZE = 300; // diameter

export function ParticleOrb({ state = 'idle' }) {
  const canvasRef = useRef(null);
  const particlesRef = useRef([]);
  const animationRef = useRef(null);

  // Initialize particles on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const centerX = ORBS_SIZE / 2;
    const centerY = ORBS_SIZE / 2;
    const radius = ORBS_SIZE / 2 - 20;

    particlesRef.current = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: centerX + (Math.random() - 0.5) * radius * 2,
      y: centerY + (Math.random() - 0.5) * radius * 2,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
      size: Math.random() * 3 + 1,
      color: `hsl(190, 100%, ${Math.random() * 30 + 50}%)`,
      trail: [],
    }));
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const centerX = ORBS_SIZE / 2;
    const centerY = ORBS_SIZE / 2;
    const radius = ORBS_SIZE / 2 - 20;

    const animate = () => {
      // Clear canvas
      ctx.clearRect(0, 0, ORBS_SIZE, ORBS_SIZE);

      // Update and draw particles
      particlesRef.current.forEach((p, i) => {
        // State-based movement
        if (state === 'idle') {
          p.vx += (Math.random() - 0.5) * 0.1;
          p.vy += (Math.random() - 0.5) * 0.1;
        } else if (state === 'listening') {
          // Pull toward center
          const dx = centerX - p.x;
          const dy = centerY - p.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          p.vx += (dx / dist) * 0.2;
          p.vy += (dy / dist) * 0.2;
        } else if (state === 'speaking') {
          // Push outward
          const dx = p.x - centerX;
          const dy = p.y - centerY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          p.vx += (dx / dist) * 0.3;
          p.vy += (dy / dist) * 0.3;
        } else if (state === 'processing') {
          // Chaotic movement
          p.vx += (Math.random() - 0.5) * 0.3;
          p.vy += (Math.random() - 0.5) * 0.3;
        }

        // Damping
        p.vx *= 0.95;
        p.vy *= 0.95;

        // Update position
        p.x += p.vx;
        p.y += p.vy;

        // Keep within bounds
        const dx = p.x - centerX;
        const dy = p.y - centerY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > radius) {
          const ratio = radius / dist;
          p.x = centerX + dx * ratio;
          p.y = centerY + dy * ratio;
        }

        // Draw trail
        p.trail.push({ x: p.x, y: p.y });
        if (p.trail.length > 15) p.trail.shift();

        ctx.strokeStyle = `rgba(${p.color.match(/\d+/g).slice(0, 3).join(',')}, 0.3)`;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        p.trail.forEach((point, i) => {
          if (i === 0) ctx.moveTo(point.x, point.y);
          else ctx.lineTo(point.x, point.y);
        });
        ctx.stroke();

        // Draw particle
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw connections (every 3rd frame for performance)
      if (Math.random() > 0.7) {
        ctx.strokeStyle = 'rgba(180, 190, 254, 0.15)';
        ctx.lineWidth = 0.5;
        particlesRef.current.forEach((p1, i) => {
          particlesRef.current.slice(i + 1).forEach(p2 => {
            const dx = p2.x - p1.x;
            const dy = p2.y - p1.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 60) {
              ctx.beginPath();
              ctx.moveTo(p1.x, p1.y);
              ctx.lineTo(p2.x, p2.y);
              ctx.stroke();
            }
          });
        });
      }

      // Draw orb outline
      ctx.strokeStyle = 'rgba(180, 190, 254, 0.4)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.stroke();

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => cancelAnimationFrame(animationRef.current);
  }, [state]);

  return (
    <div className="particle-orb-container">
      <canvas
        ref={canvasRef}
        width={ORBS_SIZE}
        height={ORBS_SIZE}
        className="particle-orb-canvas"
        data-testid={`orb-${state}`}
      />
    </div>
  );
}
