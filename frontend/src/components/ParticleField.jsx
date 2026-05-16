import { useMemo } from 'react'

export default function ParticleField({ pm25 = 0 }) {
  const bucket = Math.round(pm25 / 5) * 5
  const count = Math.max(5, Math.min(75, Math.round(bucket * 0.65)))

  const particles = useMemo(() => Array.from({ length: count }, (_, i) => {
    const dur = 10 + Math.random() * 12
    return {
      id: i,
      x: Math.random() * 100,
      size: 1.5 + Math.random() * 1.8,
      duration: dur,
      delay: -(Math.random() * dur),
    }
  }), [bucket]) // eslint-disable-line

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
      {particles.map(p => (
        <span
          key={p.id}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            bottom: 0,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.45)',
            animation: `particleFloat ${p.duration}s ${p.delay}s linear infinite`,
          }}
        />
      ))}
    </div>
  )
}
