import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const ITEMS = [
  'Đóng cửa sổ lớp học',
  'Thông báo phụ huynh qua Zalo',
  'Chuyển hoạt động thể dục vào trong',
  'Ghi nhận sự kiện vào sổ',
]

export default function ActionChecklist({ risk }) {
  const [checked, setChecked] = useState([false, false, false, false])

  useEffect(() => {
    if (risk !== 'high') setChecked([false, false, false, false])
  }, [risk])

  const toggle = i => setChecked(prev => prev.map((v, idx) => idx === i ? !v : v))
  const done = checked.filter(Boolean).length

  return (
    <AnimatePresence>
      {risk === 'high' && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="surface p-7 mb-4"
          style={{ borderColor: 'rgba(248,113,113,0.22)' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <motion.span
              style={{ width: 7, height: 7, borderRadius: '50%', background: '#f87171', display: 'block', flexShrink: 0 }}
              animate={{ scale: [1, 1.5, 1], opacity: [1, 0.45, 1] }}
              transition={{ duration: 1.3, repeat: Infinity }}
            />
            <span className="label" style={{ color: '#f87171' }}>Quy trình ứng phó — Mức CAO</span>
            <span style={{
              marginLeft: 'auto', fontSize: 11, fontFamily: 'DM Sans, sans-serif',
              color: done === ITEMS.length ? '#4ade80' : 'rgba(255,255,255,0.22)',
              transition: 'color 0.3s',
            }}>
              {done}/{ITEMS.length} hoàn thành
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
            {ITEMS.map((item, i) => (
              <div
                key={i}
                onClick={() => toggle(i)}
                style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', userSelect: 'none', padding: '2px 0' }}
              >
                <motion.span
                  animate={{
                    background: checked[i] ? '#4ade80' : 'transparent',
                    borderColor: checked[i] ? '#4ade80' : 'rgba(255,255,255,0.18)',
                  }}
                  transition={{ duration: 0.15 }}
                  style={{
                    width: 17, height: 17, borderRadius: 4,
                    border: '1.5px solid rgba(255,255,255,0.18)',
                    flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  {checked[i] && (
                    <motion.svg
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      width="9" height="9" viewBox="0 0 9 9"
                    >
                      <polyline
                        points="1,4.5 3.5,7 8,1.5"
                        stroke="#060c07" strokeWidth="1.6" fill="none"
                        strokeLinecap="round" strokeLinejoin="round"
                      />
                    </motion.svg>
                  )}
                </motion.span>
                <span style={{
                  fontFamily: 'DM Sans, sans-serif', fontSize: 13, lineHeight: 1.5,
                  color: checked[i] ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.7)',
                  textDecoration: checked[i] ? 'line-through' : 'none',
                  transition: 'color 0.2s',
                }}>
                  {item}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
