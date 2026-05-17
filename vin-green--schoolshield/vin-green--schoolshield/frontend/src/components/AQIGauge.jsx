import { useEffect, useRef } from 'react'
import { motion, useMotionValue, useSpring, animate } from 'framer-motion'

const W = 300, H = 180
const CX = W / 2, CY = H - 20
const R = 130
const STROKE = 10
const MAX_PM = 150

function polar(deg, r) {
  const rad = (deg - 180) * (Math.PI / 180)
  return [CX + r * Math.cos(rad), CY + r * Math.sin(rad)]
}

function arcD(pct) {
  const deg = Math.max(0.5, pct * 180)
  const [x1, y1] = polar(0, R)
  const [x2, y2] = polar(deg, R)
  const large = deg > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`
}

function trackD() {
  const [x1, y1] = polar(0, R)
  const [x2, y2] = polar(180, R)
  return `M ${x1} ${y1} A ${R} ${R} 0 1 1 ${x2} ${y2}`
}

function EndDot({ pct, color }) {
  const deg = pct * 180
  const [x, y] = polar(deg, R)
  return <circle cx={x} cy={y} r={5} fill={color} style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
}

export default function AQIGauge({ pm25 = 0 }) {
  const pct    = Math.min(pm25, MAX_PM) / MAX_PM
  const color  = pm25 < 35 ? '#4ade80' : pm25 < 75 ? '#fbbf24' : '#f87171'

  const glowAnim = {
    filter: [
      `drop-shadow(0 0 4px ${color})`,
      `drop-shadow(0 0 10px ${color})`,
      `drop-shadow(0 0 4px ${color})`,
    ],
    transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
  }

  return (
    <div className="flex flex-col items-center select-none">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} overflow="visible">
        <defs>
          <filter id="sg">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Zone tints */}
        <path d={arcD(35 / MAX_PM)}  fill="none" stroke="#4ade80" strokeWidth={STROKE} strokeOpacity="0.08" strokeLinecap="butt" />
        <path d={`M ${polar(35/MAX_PM*180,R).join(' ')} A ${R} ${R} 0 0 1 ${polar(75/MAX_PM*180,R).join(' ')}`}
          fill="none" stroke="#fbbf24" strokeWidth={STROKE} strokeOpacity="0.08" />
        <path d={`M ${polar(75/MAX_PM*180,R).join(' ')} A ${R} ${R} 0 0 1 ${polar(180,R).join(' ')}`}
          fill="none" stroke="#f87171" strokeWidth={STROKE} strokeOpacity="0.08" />

        {/* Track */}
        <path d={trackD()} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={STROKE} strokeLinecap="round" />

        {/* Active arc — ambient breathing via filter animation */}
        <motion.path
          d={arcD(pct)}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          animate={glowAnim}
          style={{ transition: 'd 1s cubic-bezier(0.34,1.2,0.64,1), stroke 0.8s ease' }}
        />

        {/* End dot */}
        {pct > 0.01 && <EndDot pct={pct} color={color} />}

        {/* Scale ticks */}
        {[0, 35, 75, 150].map(v => {
          const [tx, ty] = polar((v / MAX_PM) * 180, R + 18)
          return (
            <text key={v} x={tx} y={ty} textAnchor="middle" dominantBaseline="middle"
              fill="rgba(255,255,255,0.18)" fontSize="9" fontFamily="JetBrains Mono">
              {v}
            </text>
          )
        })}
      </svg>

      {/* Central value — below the arc apex */}
      <div className="flex flex-col items-center -mt-4">
        <span className="data-value leading-none" style={{ fontSize: 56, color, transition: 'color 0.8s ease' }}>
          {pm25.toFixed(1)}
        </span>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.12em', fontFamily: 'DM Sans', marginTop: 4 }}>
          µg/m³ · PM2.5
        </span>
      </div>
    </div>
  )
}
