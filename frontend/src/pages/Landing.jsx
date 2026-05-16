import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

function ShieldIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
      <path d="M32 4L8 14v18c0 14 10.5 25.5 24 28 13.5-2.5 24-14 24-28V14L32 4z"
        fill="rgba(74,222,128,0.12)" stroke="#4ade80" strokeWidth="1.5"/>
      <path d="M32 44s-12-7-12-18c0-5 4-9 8-10 0 4 2 8 6 11 4-3 6-7 6-11 4 1 8 5 8 10 0 11-16 18-16 18z"
        fill="#4ade80" fillOpacity="0.85"/>
    </svg>
  )
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
}
const item = {
  hidden: { opacity: 0, y: 32 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
}

export default function Landing() {
  const nav = useNavigate()

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6">
      {/* Animated grid background */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: 'linear-gradient(rgba(74,222,128,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(74,222,128,0.04) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      {/* Glow orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(74,222,128,0.08) 0%, transparent 70%)' }} />
      <div className="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%)' }} />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 flex flex-col items-center text-center max-w-2xl"
      >
        {/* Badge */}
        <motion.div variants={item}
          className="mb-8 flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium tracking-wider"
          style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80' }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-lime-400 animate-pulse" />
          ASIAN HACKATHON FOR GREEN FUTURE 2026
        </motion.div>

        {/* Logo */}
        <motion.div variants={item} className="mb-6">
          <ShieldIcon />
        </motion.div>

        {/* Title */}
        <motion.h1 variants={item}
          className="font-display font-bold text-6xl md:text-7xl leading-none mb-4"
          style={{ letterSpacing: '-0.03em' }}
        >
          <span className="text-white">School</span>
          <span className="text-lime-400">Shield</span>
        </motion.h1>

        {/* Tagline */}
        <motion.p variants={item}
          className="text-lg md:text-xl font-light mb-2"
          style={{ color: 'rgba(255,255,255,0.55)' }}
        >
          Hệ thống bảo vệ chất lượng không khí
        </motion.p>
        <motion.p variants={item}
          className="text-base mb-12"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Siêu cục bộ · Cổng trường · Thời gian thực
        </motion.p>

        {/* CTAs */}
        <motion.div variants={item} className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <button onClick={() => nav('/login')} className="btn-primary text-sm flex items-center justify-center gap-2 min-w-48">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
            </svg>
            Bảng Điều Khiển Desktop
          </button>
          <button onClick={() => nav('/mobile')} className="btn-ghost text-sm flex items-center justify-center gap-2 min-w-48">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="18" r="1"/>
            </svg>
            Ứng Dụng Mobile
          </button>
        </motion.div>

        {/* Stats strip */}
        <motion.div variants={item}
          className="mt-16 flex items-center gap-8 text-center"
          style={{ borderTop: '1px solid rgba(74,222,128,0.08)', paddingTop: '2rem' }}
        >
          {[
            { val: '99%', label: 'Dân số chịu ô nhiễm' },
            { val: '4.2M', label: 'Ca tử vong / năm' },
            { val: '76.7%', label: 'Phụ huynh lo ngại' },
          ].map(s => (
            <div key={s.label}>
              <p className="font-mono text-2xl font-semibold text-lime-400">{s.val}</p>
              <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.3)' }}>{s.label}</p>
            </div>
          ))}
        </motion.div>
      </motion.div>

      {/* Bottom label */}
      <motion.p
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.2 }}
        className="absolute bottom-6 text-xs font-mono"
        style={{ color: 'rgba(255,255,255,0.15)' }}
      >
        SchoolShield · Dữ liệu mô phỏng · Hà Nội, Việt Nam
      </motion.p>
    </div>
  )
}
