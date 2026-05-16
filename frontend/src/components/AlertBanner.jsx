import { motion, AnimatePresence } from 'framer-motion'

export default function AlertBanner({ alerts = [], onDismiss }) {
  const top = alerts.find(a => !a.dismissed && a.level === 'high')

  return (
    <AnimatePresence>
      {top && (
        <motion.div key={top.id}
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{ borderBottom: '1px solid rgba(248,113,113,0.15)', background: 'rgba(248,113,113,0.06)', overflow: 'hidden' }}
        >
          <div className="flex items-center justify-between gap-4 px-8 py-3 max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <motion.span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0"
                animate={{ opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.5, repeat: Infinity }} />
              <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)' }}>
                <span style={{ color: '#f87171', fontWeight: 600 }}>CẢNH BÁO — </span>
                {top.message}
              </p>
            </div>
            <button onClick={() => onDismiss(top.id)}
              style={{ color: 'rgba(255,255,255,0.3)', fontSize: 18, lineHeight: 1, flexShrink: 0 }}
              onMouseEnter={e => e.currentTarget.style.color = 'rgba(255,255,255,0.7)'}
              onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.3)'}
            >✕</button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
