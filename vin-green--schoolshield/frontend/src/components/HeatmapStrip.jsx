import { useState } from 'react'

// Reflects elevated Hanoi baseline (medium all day) + high peaks at 07:30 and 16:00
const HOUR_RISK = [
  'low','low','low','low','low','medium',
  'medium','high','high','medium','medium','medium',
  'medium','medium','medium','high','high','medium',
  'medium','medium','low','low','low','low',
]
const RISK_COLOR = { low: '#4ade80', medium: '#fbbf24', high: '#f87171' }
const RISK_LABEL = { low: 'An toàn', medium: 'Cần lưu ý', high: 'Nguy hiểm' }

export default function HeatmapStrip() {
  const [hovered, setHovered] = useState(null)
  const currentHour = new Date().getHours()

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span className="label" style={{ fontSize: 10 }}>Dự báo rủi ro 24 giờ</span>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', minWidth: 120, textAlign: 'right' }}>
          {hovered !== null
            ? <>{String(hovered).padStart(2,'0')}:00 — <span style={{ color: RISK_COLOR[HOUR_RISK[hovered]] }}>{RISK_LABEL[HOUR_RISK[hovered]]}</span></>
            : 'Di chuyển để xem chi tiết'
          }
        </span>
      </div>
      <div style={{ display: 'flex', gap: 2, height: 18, borderRadius: 4, overflow: 'hidden' }}>
        {HOUR_RISK.map((risk, hour) => {
          const isPast = hour < currentHour
          const isCurrent = hour === currentHour
          const opacity = hovered === hour ? 0.95 : isCurrent ? 1 : isPast ? 0.3 : 0.48
          return (
            <div
              key={hour}
              onMouseEnter={() => setHovered(hour)}
              onMouseLeave={() => setHovered(null)}
              style={{
                flex: 1,
                background: RISK_COLOR[risk],
                opacity,
                transition: 'opacity 0.12s',
                outline: isCurrent ? '1px solid rgba(255,255,255,0.5)' : 'none',
                outlineOffset: -1,
                cursor: 'default',
              }}
            />
          )
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, paddingRight: 2 }}>
        {[0, 6, 12, 18, 23].map(h => (
          <span key={h} style={{ fontSize: 9, color: 'rgba(255,255,255,0.18)', fontFamily: 'JetBrains Mono, monospace' }}>
            {String(h).padStart(2,'0')}h
          </span>
        ))}
      </div>
    </div>
  )
}
