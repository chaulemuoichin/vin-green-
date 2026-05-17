import { useState, useEffect } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import Sidebar from '../components/Sidebar'
import AQIGauge from '../components/AQIGauge'
import RiskBadge from '../components/RiskBadge'
import AlertBanner from '../components/AlertBanner'
import IdlingCounter from '../components/IdlingCounter'
import TrendChart from '../components/TrendChart'
import MapPin from '../components/MapPin'
import Analytics from './Analytics'
import { useAQI } from '../hooks/useAQI'
import { useAlerts } from '../hooks/useAlerts'

function LiveClock() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className="font-mono text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
      {time.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
}
const cardAnim = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
}

function MetricCard({ label, value, unit, color, icon, sub }) {
  return (
    <motion.div variants={cardAnim} className="card p-5 flex flex-col gap-2">
      <div className="flex items-start justify-between">
        <p className="stat-label">{label}</p>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: 'rgba(74,222,128,0.08)' }}>
          {icon}
        </div>
      </div>
      <p className={`font-mono text-3xl font-semibold tabular-nums`} style={{ color }}>
        {value}
        {unit && <span className="text-sm font-normal ml-1" style={{ color: 'rgba(255,255,255,0.35)' }}>{unit}</span>}
      </p>
      {sub && <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>{sub}</p>}
    </motion.div>
  )
}

function MainDashboard() {
  const { current, history } = useAQI()
  const { alerts, dismiss } = useAlerts()

  const pm25 = current?.pm25 ?? 0
  const risk = current?.risk ?? 'low'
  const idling = current?.idling_count ?? 0
  const activeAlerts = alerts.filter(a => !a.dismissed)

  const riskColor = risk === 'high' ? '#ef4444' : risk === 'medium' ? '#f59e0b' : '#4ade80'

  return (
    <div className="flex flex-col h-full">
      <AlertBanner alerts={alerts} onDismiss={dismiss} />

      <div className="flex-1 overflow-y-auto p-6">
        {/* Metric cards row */}
        <motion.div variants={stagger} initial="hidden" animate="show"
          className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-5"
        >
          <MetricCard
            label="PM2.5 Hiện tại"
            value={pm25.toFixed(1)}
            unit="µg/m³"
            color={riskColor}
            sub="Cập nhật 5 giây"
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>}
          />
          <MetricCard
            label="Xe đang nổ máy"
            value={idling}
            unit="xe"
            color="#f59e0b"
            sub="Ước tính từ camera"
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2"><path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v9a2 2 0 0 1-2 2h-2"/><circle cx="9" cy="19" r="2"/><circle cx="17" cy="19" r="2"/></svg>}
          />
          <MetricCard
            label="Cảnh báo hôm nay"
            value={activeAlerts.length}
            unit="cảnh báo"
            color={activeAlerts.length > 0 ? '#ef4444' : '#4ade80'}
            sub={activeAlerts.length > 0 ? 'Đang hoạt động' : 'Tất cả đã giải quyết'}
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/></svg>}
          />
          <MetricCard
            label="Thời gian phơi nhiễm"
            value="24"
            unit="phút"
            color="rgba(255,255,255,0.7)"
            sub="Mức cao hôm nay"
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
          />
        </motion.div>

        {/* Middle: Gauge + RiskBadge left, Map right */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-5">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.6 }}
            className="card p-6 flex flex-col gap-5"
          >
            <div className="flex items-center justify-between">
              <p className="stat-label">Chỉ số không khí</p>
              <div className="flex items-center gap-2 text-xs font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-lime-400 animate-pulse" />
                Theo dõi trực tiếp
              </div>
            </div>
            <div className="flex flex-col items-center">
              <AQIGauge pm25={pm25} />
            </div>
            <RiskBadge risk={risk} />
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.6 }}
            className="card overflow-hidden flex flex-col"
          >
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <p className="stat-label">Vị trí cảm biến</p>
              <span className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
                21.0285°N 105.8485°E
              </span>
            </div>
            <div className="flex-1" style={{ minHeight: '220px' }}>
              <MapPin pm25={pm25} risk={risk} />
            </div>
          </motion.div>
        </div>

        {/* Trend chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.6 }}
          className="mb-5"
        >
          <TrendChart data={history} />
        </motion.div>

        {/* Alert log */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6, duration: 0.6 }}
          className="card p-5"
        >
          <p className="stat-label mb-4">Nhật ký cảnh báo</p>
          {alerts.length === 0 ? (
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.3)' }}>Không có cảnh báo nào.</p>
          ) : (
            <div className="divide-y" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
              {alerts.map(a => {
                const c = a.level === 'high' ? '#ef4444' : a.level === 'medium' ? '#f59e0b' : '#4ade80'
                return (
                  <div key={a.id} className={`flex items-start justify-between py-3 gap-4 ${a.dismissed ? 'opacity-40' : ''}`}>
                    <div className="flex items-start gap-3">
                      <span className="mt-1 w-2 h-2 rounded-full flex-shrink-0" style={{ background: c }} />
                      <p className="text-sm" style={{ color: 'rgba(255,255,255,0.75)' }}>{a.message}</p>
                    </div>
                    <span className="text-xs flex-shrink-0 font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
                      {new Date(a.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default function DesktopDashboard() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />

      {/* Main area */}
      <div className="flex-1 flex flex-col" style={{ marginLeft: '240px' }}>
        {/* Top header */}
        <header className="sticky top-0 z-20 flex items-center justify-between px-6 h-14"
          style={{ background: 'rgba(3,13,6,0.85)', borderBottom: '1px solid rgba(74,222,128,0.08)', backdropFilter: 'blur(12px)' }}
        >
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-lime-400 animate-pulse" />
            <span className="text-sm font-medium text-white">THCS Nguyễn Trãi — Cổng chính</span>
          </div>
          <div className="flex items-center gap-4">
            <LiveClock />
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs"
              style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.15)', color: '#4ade80' }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-lime-400 animate-pulse" />
              Đang theo dõi
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-hidden">
          <Routes>
            <Route index element={<MainDashboard />} />
            <Route path="analytics" element={<div className="p-6"><Analytics /></div>} />
            <Route path="alerts" element={
              <div className="p-6 flex items-center justify-center h-64">
                <p style={{ color: 'rgba(255,255,255,0.3)' }}>Trang cảnh báo — sắp ra mắt</p>
              </div>
            } />
            <Route path="settings" element={
              <div className="p-6 flex items-center justify-center h-64">
                <p style={{ color: 'rgba(255,255,255,0.3)' }}>Cài đặt — sắp ra mắt</p>
              </div>
            } />
          </Routes>
        </div>
      </div>
    </div>
  )
}
