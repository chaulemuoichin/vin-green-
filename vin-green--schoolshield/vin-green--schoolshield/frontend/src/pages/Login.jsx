import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function Login() {
  const nav = useNavigate()
  const [loading, setLoading] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => nav('/desktop'), 1200)
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      {/* Grid bg */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: 'linear-gradient(rgba(74,222,128,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(74,222,128,0.03) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] pointer-events-none"
        style={{ background: 'radial-gradient(ellipse, rgba(74,222,128,0.08) 0%, transparent 70%)' }} />

      <motion.div
        initial={{ opacity: 0, y: 40, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 w-full max-w-sm"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <svg width="28" height="28" viewBox="0 0 64 64" fill="none">
              <path d="M32 4L8 14v18c0 14 10.5 25.5 24 28 13.5-2.5 24-14 24-28V14L32 4z"
                fill="rgba(74,222,128,0.15)" stroke="#4ade80" strokeWidth="2"/>
              <path d="M32 44s-12-7-12-18c0-5 4-9 8-10 0 4 2 8 6 11 4-3 6-7 6-11 4 1 8 5 8 10 0 11-16 18-16 18z"
                fill="#4ade80"/>
            </svg>
            <span className="font-display font-bold text-xl">
              <span className="text-white">School</span><span className="text-lime-400">Shield</span>
            </span>
          </div>
          <h2 className="font-display text-2xl font-semibold text-white mb-1">Đăng nhập</h2>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Hệ thống quản lý chất lượng không khí</p>
        </div>

        {/* Card */}
        <form onSubmit={handleSubmit} className="card p-8 flex flex-col gap-5">
          <div>
            <label className="stat-label mb-2 block">Trường học</label>
            <input
              type="text"
              defaultValue="THCS Nguyễn Trãi, Hà Nội"
              className="w-full px-4 py-3 rounded-xl text-sm font-medium text-white outline-none transition-all"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(74,222,128,0.15)',
              }}
              onFocus={e => e.target.style.borderColor = 'rgba(74,222,128,0.4)'}
              onBlur={e => e.target.style.borderColor = 'rgba(74,222,128,0.15)'}
            />
          </div>
          <div>
            <label className="stat-label mb-2 block">Mật khẩu</label>
            <input
              type="password"
              defaultValue="••••••••"
              className="w-full px-4 py-3 rounded-xl text-sm font-medium text-white outline-none transition-all"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(74,222,128,0.15)',
              }}
              onFocus={e => e.target.style.borderColor = 'rgba(74,222,128,0.4)'}
              onBlur={e => e.target.style.borderColor = 'rgba(74,222,128,0.15)'}
            />
          </div>

          <button type="submit" disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 mt-2 relative overflow-hidden"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"/>
                </svg>
                Đang kết nối...
              </>
            ) : 'Đăng nhập →'}
          </button>

          <p className="text-xs text-center" style={{ color: 'rgba(255,255,255,0.25)' }}>
            Prototype · Không cần xác thực thực tế
          </p>
        </form>

        <button onClick={() => nav(-1)}
          className="mt-4 w-full text-center text-xs py-2 transition-colors"
          style={{ color: 'rgba(255,255,255,0.3)' }}
          onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.6)'}
          onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.3)'}
        >
          ← Quay lại trang chủ
        </button>
      </motion.div>
    </div>
  )
}
