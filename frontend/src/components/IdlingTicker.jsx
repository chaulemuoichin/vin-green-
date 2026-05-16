import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const fade = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

export default function IdlingTicker({ idling = 0, risk = 'low', className = 'surface p-6 flex flex-col gap-2' }) {
  const [seconds, setSeconds] = useState(0)
  const [prevIdling, setPrevIdling] = useState(idling)

  useEffect(() => {
    const id = setInterval(() => setSeconds(s => s + 1), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (idling !== prevIdling) setPrevIdling(idling)
  }, [idling, prevIdling])

  const idlingColor = idling > 5 ? '#f87171' : idling > 2 ? '#fbbf24' : '#4ade80'
  const co2PerMin = idling * 40
  const totalCO2g = Math.round(co2PerMin * (seconds / 60))
  const co2Display = totalCO2g >= 1000 ? `${(totalCO2g / 1000).toFixed(2)} kg` : `${totalCO2g} g`

  return (
    <motion.div variants={fade} className={className}>
      <span className="label">Xe đang nổ máy</span>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <AnimatePresence mode="wait">
          <motion.p
            key={idling}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.25 }}
            className="data-value leading-none"
            style={{ fontSize: 36, color: idlingColor }}
          >
            {idling}
          </motion.p>
        </AnimatePresence>
        <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontWeight: 400 }}>xe</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
        <motion.span
          style={{ width: 5, height: 5, borderRadius: '50%', background: idlingColor, flexShrink: 0, display: 'inline-block' }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif', lineHeight: 1.4 }}>
          ~{co2PerMin} g CO₂/phút · Tích lũy: {co2Display}
        </p>
      </div>
    </motion.div>
  )
}
