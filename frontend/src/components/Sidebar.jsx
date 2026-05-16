import { NavLink, useNavigate } from 'react-router-dom'

const navItems = [
  {
    to: '/desktop',
    label: 'Bảng Điều Khiển',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
    ),
  },
  {
    to: '/desktop/analytics',
    label: 'Phân Tích',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
  },
  {
    to: '/desktop/alerts',
    label: 'Cảnh Báo',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
    ),
  },
  {
    to: '/desktop/settings',
    label: 'Cài Đặt',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>
      </svg>
    ),
  },
]

export default function Sidebar() {
  const nav = useNavigate()

  return (
    <aside className="fixed left-0 top-0 h-full w-[240px] flex flex-col z-30"
      style={{ background: '#0b1e10', borderRight: '1px solid rgba(74,222,128,0.08)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5"
        style={{ borderBottom: '1px solid rgba(74,222,128,0.08)' }}
      >
        <svg width="30" height="30" viewBox="0 0 64 64" fill="none">
          <path d="M32 4L8 14v18c0 14 10.5 25.5 24 28 13.5-2.5 24-14 24-28V14L32 4z"
            fill="rgba(74,222,128,0.15)" stroke="#4ade80" strokeWidth="1.5"/>
          <path d="M32 44s-12-7-12-18c0-5 4-9 8-10 0 4 2 8 6 11 4-3 6-7 6-11 4 1 8 5 8 10 0 11-16 18-16 18z"
            fill="#4ade80"/>
        </svg>
        <div>
          <span className="font-display font-bold text-base text-white">School</span>
          <span className="font-display font-bold text-base text-lime-400">Shield</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/desktop'}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            {icon}
            <span className="text-sm">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* School tag */}
      <div className="px-5 py-4" style={{ borderTop: '1px solid rgba(74,222,128,0.08)' }}>
        <div className="flex items-center gap-2.5 p-3 rounded-xl"
          style={{ background: 'rgba(74,222,128,0.05)' }}
        >
          <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(74,222,128,0.15)' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-white truncate">THCS Nguyễn Trãi</p>
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>Hà Nội · Cổng chính</p>
          </div>
        </div>
        <button onClick={() => nav('/')}
          className="mt-2 w-full text-xs py-2 text-center rounded-lg transition-all"
          style={{ color: 'rgba(255,255,255,0.3)' }}
          onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.6)'}
          onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.3)'}
        >
          ← Trang chủ
        </button>
      </div>
    </aside>
  )
}
