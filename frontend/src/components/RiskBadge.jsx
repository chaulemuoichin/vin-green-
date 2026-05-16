import { motion, AnimatePresence } from 'framer-motion'

const CFG = {
  low:    { vi: 'THẤP',       en: 'Low',    color: '#4ade80', ring: 'rgba(74,222,128,0.2)' },
  medium: { vi: 'TRUNG BÌNH', en: 'Medium', color: '#fbbf24', ring: 'rgba(251,191,36,0.2)' },
  high:   { vi: 'CAO',        en: 'High',   color: '#f87171', ring: 'rgba(248,113,113,0.2)' },
}

export default function RiskBadge({ risk = 'low' }) {
  const c = CFG[risk] ?? CFG.low

  return (
    <div className="flex flex-col items-center gap-3">
      <span className="label">Mức độ rủi ro</span>

      <AnimatePresence mode="wait">
        <motion.div key={risk}
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.88 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="relative flex items-center justify-center gap-2.5 px-8 py-3.5 rounded-full"
          style={{ border: `1px solid ${c.ring}`, background: `${c.ring.replace('0.2', '0.07')}` }}
        >
          {/* Breathing ring */}
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{ border: `1px solid ${c.color}` }}
            animate={{ opacity: [0.3, 0.7, 0.3], scale: [1, 1.04, 1] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          />

          <motion.span className="relative w-2 h-2 rounded-full"
            style={{ background: c.color, boxShadow: `0 0 8px ${c.color}` }}
            animate={{ opacity: [0.7, 1, 0.7], scale: [0.9, 1.1, 0.9] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />

          <span className="relative font-sans font-semibold tracking-widest text-sm" style={{ color: c.color }}>
            {c.vi}
          </span>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
