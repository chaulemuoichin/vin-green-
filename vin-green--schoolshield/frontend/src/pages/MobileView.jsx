import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAQI } from '../hooks/useAQI'
import { useAlerts } from '../hooks/useAlerts'
import { usePersona } from '../context/PersonaContext'
import TrendChart from '../components/TrendChart'
import MapPin from '../components/MapPin'

// ── Icons ──────────────────────────────────────────────────────────
const IcoHome     = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
const IcoMap      = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>
const IcoHistory  = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="12 8 12 12 14 14"/><path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"/></svg>
const IcoBell     = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
const IcoMonitor  = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
const IcoChart    = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
const IcoBroadcast = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>

const PARENT_TABS = [
  { id: 'home',   label: 'Tổng quan', Icon: IcoHome },
  { id: 'map',    label: 'Bản đồ',    Icon: IcoMap },
  { id: 'chart',  label: 'Lịch sử',   Icon: IcoHistory },
  { id: 'alerts', label: 'Nhắc nhở',  Icon: IcoBell },
]
const SCHOOL_TABS = [
  { id: 'home',   label: 'Theo dõi',  Icon: IcoMonitor },
  { id: 'map',    label: 'Bản đồ',    Icon: IcoMap },
  { id: 'chart',  label: 'Phân tích', Icon: IcoChart },
  { id: 'alerts', label: 'Phát sóng', Icon: IcoBroadcast },
]

function getSafeWindow() {
  const now = new Date()
  const t = now.getHours() * 60 + now.getMinutes()
  if (t < 7 * 60 + 15)  return { time: '07:15', safe: true,  note: 'Trước cao điểm sáng' }
  if (t < 8 * 60 + 20)  return { time: '08:20', safe: false, note: 'Đang cao điểm — chờ thêm' }
  if (t < 15 * 60 + 40) return { time: '15:40', safe: true,  note: 'Trước cao điểm chiều' }
  if (t < 17 * 60)      return { time: '17:00', safe: false, note: 'Đang cao điểm — chờ thêm' }
  return { time: 'Ngay bây giờ', safe: true, note: 'Không khí đã cải thiện' }
}

const HEALTH = {
  low:    {
    status: 'AN TOÀN',
    verdict: 'CÓ THỂ ĐÓN TRẺ',
    sub: 'Không khí trong lành, an toàn cho trẻ',
    tips: ['Mở cửa sổ xe khi đón', 'Trẻ ra ngoài bình thường'],
  },
  medium: {
    status: 'CẦN LƯU Ý',
    verdict: 'NÊN LƯU Ý KHI ĐÓN',
    sub: 'Lượng xe còn nhiều, khói bụi tăng nhẹ',
    tips: ['Đóng kính xe khi đón', 'Không để xe nổ máy chờ', 'Đón nhanh rồi vào xe'],
  },
  high: {
    status: 'NGUY HIỂM',
    verdict: 'HẠN CHẾ TIẾP XÚC',
    sub: 'Chỉ số bụi mịn cao, không tốt cho trẻ nhỏ',
    tips: ['Đeo khẩu trang cho trẻ', 'Đón thật nhanh', 'Bật lọc không khí trong xe'],
  },
}

const STATIONS = [
  { name: 'Cổng chính', mult: 1.0,  offset: 0,  main: true  },
  { name: 'Cổng sau',   mult: 0.82, offset: -4, main: false },
  { name: 'Tường đông', mult: 0.88, offset: 2,  main: false },
  { name: 'Tường tây',  mult: 1.18, offset: 5,  main: false },
  { name: 'Bãi đỗ xe',  mult: 1.1,  offset: 3,  main: false },
]

// ── Phụ huynh: verdict-first, action-oriented ─────────────────────
function ParentHome({ risk, riskColor, pm25, safeWin, health }) {
  const ok = safeWin.safe && risk !== 'high'
  const verdictColor = ok ? '#4ade80' : '#fbbf24'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* VERDICT HERO */}
      <motion.div
        key={`${risk}-${ok}`}
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        style={{
          borderRadius: 22, padding: '22px 20px',
          background: `linear-gradient(135deg, ${verdictColor}14 0%, ${verdictColor}05 100%)`,
          border: `1px solid ${verdictColor}30`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <motion.span
            style={{ width: 7, height: 7, borderRadius: '50%', background: verdictColor, display: 'block' }}
            animate={{ opacity: [1, 0.3, 1], scale: [1, 1.5, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <span style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>
            Live · {new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <p style={{ fontFamily: 'Be Vietnam Pro, sans-serif', fontWeight: 900, fontSize: 28, lineHeight: 1.15, color: verdictColor, marginBottom: 8, letterSpacing: '-0.02em' }}>
          {health.verdict}
        </p>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', fontFamily: 'DM Sans, sans-serif', lineHeight: 1.55 }}>{health.sub}</p>
      </motion.div>

      {/* PICKUP TIME + AQI PILL */}
      <div style={{ borderRadius: 18, padding: '16px 18px', background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', marginBottom: 8 }}>Giờ đón tốt nhất</p>
          <motion.p
            style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: 42, color: safeWin.safe ? '#4ade80' : '#fbbf24', lineHeight: 1 }}
            animate={{ opacity: [0.8, 1, 0.8] }} transition={{ duration: 3.5, repeat: Infinity }}
          >{safeWin.time}</motion.p>
          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontFamily: 'DM Sans, sans-serif', marginTop: 6 }}>{safeWin.note}</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5, padding: '12px 14px', borderRadius: 16, background: `${riskColor}10`, border: `1px solid ${riskColor}22` }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 700, color: riskColor, lineHeight: 1 }}>{pm25.toFixed(0)}</span>
          <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', letterSpacing: '0.08em' }}>µg/m³</span>
          <span style={{ fontSize: 9, padding: '2px 9px', borderRadius: 20, background: `${riskColor}20`, color: riskColor, fontFamily: 'DM Sans, sans-serif', fontWeight: 700 }}>
            {health.status}
          </span>
        </div>
      </div>

      {/* ACTION CHECKLIST */}
      <div style={{ borderRadius: 16, padding: '16px', background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <p style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', marginBottom: 13 }}>Cần làm khi đón con</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {health.tips.map((tip, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <span style={{ width: 20, height: 20, borderRadius: 6, border: `1.5px solid ${riskColor}50`, background: `${riskColor}12`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                  <path d="M1 4L3.8 7L9 1" stroke={riskColor} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </span>
              <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', fontFamily: 'DM Sans, sans-serif', lineHeight: 1.55 }}>{tip}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FOOTER SUMMARY */}
      <div style={{ borderRadius: 12, padding: '12px 14px', background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: 10, alignItems: 'center' }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={riskColor} strokeWidth="1.5" opacity="0.55" style={{ flexShrink: 0 }}>
          <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
        </svg>
        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', fontFamily: 'DM Sans, sans-serif', lineHeight: 1.55 }}>
          Không khí trường hiện ở mức{' '}
          <span style={{ color: riskColor, fontWeight: 600 }}>{health.status.toLowerCase()}</span>.
          PM2.5: {pm25.toFixed(1)} µg/m³
        </p>
      </div>
    </div>
  )
}

// ── Nhà trường: monitoring dashboard, data-dense ──────────────────
function SchoolHome({ risk, riskColor, pm25, idling, activeAlerts }) {
  const classrooms = risk === 'high' ? 12 : risk === 'medium' ? 6 : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {activeAlerts.length > 0 && (
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 12, padding: '10px 14px', fontSize: 12, color: 'rgba(255,255,255,0.75)', lineHeight: 1.5, fontFamily: 'DM Sans, sans-serif' }}>
          <span style={{ color: '#f87171', fontWeight: 700, letterSpacing: '0.04em' }}>CẢNH BÁO · </span>{activeAlerts[0].message}
        </div>
      )}

      {/* PRIMARY METRICS */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div style={{ background: `linear-gradient(145deg, ${riskColor}18 0%, ${riskColor}06 100%)`, border: `1px solid ${riskColor}28`, borderRadius: 18, padding: '16px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 10 }}>
            <motion.span style={{ width: 5, height: 5, borderRadius: '50%', background: riskColor, display: 'block' }}
              animate={{ opacity: [1, 0.2, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
            <span style={{ fontSize: 9, letterSpacing: '0.11em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>PM2.5 LIVE</span>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 34, fontWeight: 700, color: riskColor, lineHeight: 1 }}>{pm25.toFixed(1)}</p>
          <p style={{ fontSize: 9, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif', marginTop: 5 }}>µg/m³ · Cổng chính</p>
        </div>

        <div style={{ background: 'linear-gradient(145deg, rgba(251,191,36,0.12) 0%, rgba(251,191,36,0.04) 100%)', border: '1px solid rgba(251,191,36,0.22)', borderRadius: 18, padding: '16px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 10 }}>
            <motion.span style={{ width: 5, height: 5, borderRadius: '50%', background: '#fbbf24', display: 'block' }}
              animate={{ opacity: [1, 0.2, 1] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }} />
            <span style={{ fontSize: 9, letterSpacing: '0.11em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>XE NỔ MÁY</span>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 34, fontWeight: 700, color: '#fbbf24', lineHeight: 1 }}>{idling}</p>
          <p style={{ fontSize: 9, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif', marginTop: 5 }}>xe · thời điểm này</p>
        </div>
      </div>

      {/* SECONDARY STATS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {[
          { label: 'Học sinh', val: '420', color: '#a78bfa' },
          { label: 'Phòng ảnh hưởng', val: String(classrooms), color: classrooms > 0 ? '#f87171' : '#4ade80' },
          { label: 'Trạm online', val: '5/5', color: '#4ade80' },
        ].map(m => (
          <div key={m.label} style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12, padding: '12px 8px', textAlign: 'center' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700, color: m.color, lineHeight: 1 }}>{m.val}</p>
            <p style={{ fontSize: 9, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif', marginTop: 5, lineHeight: 1.4 }}>{m.label}</p>
          </div>
        ))}
      </div>

      {/* SENSOR NETWORK */}
      <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, overflow: 'hidden' }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 7 }}>
          <motion.span style={{ width: 5, height: 5, borderRadius: '50%', background: '#4ade80', display: 'block' }}
            animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 2, repeat: Infinity }} />
          <p style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif' }}>Mạng lưới cảm biến · 5 trạm</p>
        </div>
        {STATIONS.map((s, i) => {
          const sp = Math.max(8, Math.round(pm25 * s.mult + s.offset))
          const sc = sp < 35 ? '#4ade80' : sp < 75 ? '#fbbf24' : '#f87171'
          const pct = Math.min(sp / 150, 1)
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', padding: '9px 14px', borderBottom: i < 4 ? '1px solid rgba(255,255,255,0.04)' : 'none', gap: 10 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: sc, flexShrink: 0, boxShadow: `0 0 6px ${sc}70` }} />
              <span style={{ flex: 1, fontSize: 11, color: s.main ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.5)', fontFamily: 'DM Sans, sans-serif' }}>
                {s.name}
                {s.main && <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.22)', marginLeft: 5 }}>· chính</span>}
              </span>
              <div style={{ width: 36, height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                <div style={{ width: `${pct * 100}%`, height: '100%', background: sc, borderRadius: 2 }} />
              </div>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: sc, fontWeight: 600, minWidth: 22, textAlign: 'right' }}>{sp}</span>
            </div>
          )
        })}
      </div>

      {/* QUICK ACTIONS */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <button style={{ borderRadius: 12, padding: '11px 8px', background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80', fontSize: 11, fontFamily: 'DM Sans, sans-serif', fontWeight: 600, cursor: 'pointer' }}>
          Thông báo phụ huynh
        </button>
        <button style={{ borderRadius: 12, padding: '11px 8px', background: 'rgba(248,113,113,0.07)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171', fontSize: 11, fontFamily: 'DM Sans, sans-serif', fontWeight: 600, cursor: 'pointer' }}>
          Phát cảnh báo
        </button>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────
export default function MobileView() {
  const [tab, setTab] = useState('home')
  const { current, history } = useAQI()
  const { alerts, dismiss } = useAlerts()
  const { persona, setPersona } = usePersona()
  const nav = useNavigate()

  const pm25   = current?.pm25 ?? 0
  const risk   = current?.risk ?? 'low'
  const idling = current?.idling_count ?? 0
  const riskColor   = risk === 'high' ? '#f87171' : risk === 'medium' ? '#fbbf24' : '#4ade80'
  const activeAlerts = alerts.filter(a => !a.dismissed)
  const safeWin = getSafeWindow()
  const health  = HEALTH[risk] || HEALTH.low

  const TABS = persona === 'parent' ? PARENT_TABS : SCHOOL_TABS

  useEffect(() => { document.body.dataset.risk = risk }, [risk])
  useEffect(() => { setTab('home') }, [persona])

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-8"
      style={{ background: 'radial-gradient(ellipse 80% 50% at 50% 20%, rgba(74,222,128,0.05) 0%, transparent 60%), #060c07' }}
    >
      <button onClick={() => nav('/')}
        style={{ position: 'fixed', top: 24, left: 32, fontSize: 12, color: 'rgba(255,255,255,0.25)', fontFamily: 'DM Sans, sans-serif', cursor: 'pointer', transition: 'color 0.2s', background: 'none', border: 'none' }}
        onMouseEnter={e => e.currentTarget.style.color = 'rgba(255,255,255,0.6)'}
        onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.25)'}
      >← Desktop</button>

      <motion.div
        initial={{ opacity: 0, y: -40, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        style={{ width: 390, height: 844, position: 'relative' }}
      >
        {/* Bezel */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: 52, background: '#111', zIndex: 10, pointerEvents: 'none', boxShadow: '0 0 0 1px rgba(255,255,255,0.07), 0 40px 80px rgba(0,0,0,0.7)' }} />
        {/* Side buttons */}
        {[{ l: true, t: 112, h: 40 }, { l: true, t: 176, h: 64 }, { l: true, t: 256, h: 64 }, { l: false, t: 160, h: 80 }].map((b, i) => (
          <div key={i} style={{ position: 'absolute', zIndex: 15, [b.l ? 'left' : 'right']: -3, top: b.t, width: 3, height: b.h, borderRadius: b.l ? '2px 0 0 2px' : '0 2px 2px 0', background: 'rgba(255,255,255,0.08)' }} />
        ))}

        {/* Screen */}
        <div style={{ position: 'absolute', inset: 3, borderRadius: 49, overflow: 'hidden', background: '#060c07', zIndex: 20, display: 'flex', flexDirection: 'column' }}>

          {/* Status bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 28px 8px', flexShrink: 0 }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.8)' }}>
              {new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
            </span>
            <div style={{ width: 100, height: 22, background: '#111', borderRadius: '0 0 14px 14px' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <svg width="13" height="9" viewBox="0 0 13 9" fill="white"><rect x="0" y="3" width="2" height="6" rx=".5" fillOpacity=".4"/><rect x="3" y="2" width="2" height="7" rx=".5" fillOpacity=".6"/><rect x="6" y="0" width="2" height="9" rx=".5" fillOpacity=".8"/><rect x="9" y="0" width="2" height="9" rx=".5"/></svg>
              <div style={{ width: 18, height: 10, borderRadius: 3, border: '1px solid rgba(255,255,255,0.4)', padding: '1px' }}>
                <div style={{ width: '75%', height: '100%', borderRadius: 2, background: 'white' }} />
              </div>
            </div>
          </div>

          {/* App header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px 10px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 }}>
                <svg width="16" height="16" viewBox="0 0 64 64" fill="none">
                  <path d="M32 4L8 14v18c0 14 10.5 25.5 24 28 13.5-2.5 24-14 24-28V14L32 4z" fill="rgba(74,222,128,0.15)" stroke="#4ade80" strokeWidth="2"/>
                  <path d="M32 44s-12-7-12-18c0-5 4-9 8-10 0 4 2 8 6 11 4-3 6-7 6-11 4 1 8 5 8 10 0 11-16 18-16 18z" fill="#4ade80"/>
                </svg>
                <span style={{ fontFamily: 'DM Sans, sans-serif', fontWeight: 700, fontSize: 14, color: 'rgba(255,255,255,0.92)' }}>
                  School<span style={{ color: '#4ade80' }}>Shield</span>
                </span>
              </div>
              <AnimatePresence mode="wait">
                <motion.p
                  key={persona}
                  initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 5 }}
                  transition={{ duration: 0.18 }}
                  style={{ fontSize: 10, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif', letterSpacing: '0.04em' }}
                >
                  {persona === 'parent' ? 'Đón con an toàn · THCS Nguyễn Trãi' : 'Giám sát · Cổng trường · Live'}
                </motion.p>
              </AnimatePresence>
            </div>

            {/* Persona toggle */}
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 9, padding: 2, gap: 1 }}>
              {[['parent', 'Phụ huynh'], ['school', 'Trường']].map(([id, label]) => (
                <button key={id} onClick={() => setPersona(id)}
                  style={{
                    fontFamily: 'DM Sans, sans-serif', fontSize: 10, fontWeight: 600,
                    padding: '4px 10px', borderRadius: 7, border: 'none', cursor: 'pointer',
                    background: persona === id ? 'rgba(74,222,128,0.14)' : 'transparent',
                    color: persona === id ? '#4ade80' : 'rgba(255,255,255,0.3)',
                    transition: 'all 0.2s',
                  }}
                >{label}</button>
              ))}
            </div>
          </div>

          {/* Content area */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '14px 14px 0' }}>

            {/* HOME TAB */}
            <AnimatePresence mode="wait">
              {tab === 'home' && (
                <motion.div
                  key={`home-${persona}`}
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.22 }}
                >
                  {persona === 'parent'
                    ? <ParentHome risk={risk} riskColor={riskColor} pm25={pm25} safeWin={safeWin} health={health} />
                    : <SchoolHome risk={risk} riskColor={riskColor} pm25={pm25} idling={idling} activeAlerts={activeAlerts} />
                  }
                </motion.div>
              )}
            </AnimatePresence>

            {/* MAP TAB — always mounted to avoid Leaflet remount */}
            <div style={{ display: tab === 'map' ? 'block' : 'none', borderRadius: 18, overflow: 'hidden', height: 460, border: '1px solid rgba(255,255,255,0.07)' }}>
              <MapPin pm25={pm25} risk={risk} />
            </div>

            {/* CHART TAB */}
            {tab === 'chart' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
                <TrendChart data={history} />
              </motion.div>
            )}

            {/* ALERTS / BROADCAST TAB */}
            {tab === 'alerts' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {/* School gets broadcast button */}
                  {persona === 'school' && (
                    <button style={{ borderRadius: 12, padding: '12px', background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80', fontSize: 12, fontFamily: 'DM Sans, sans-serif', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                      <IcoBroadcast />
                      Phát cảnh báo toàn trường
                    </button>
                  )}

                  <p style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif' }}>
                    {persona === 'parent' ? 'Nhắc nhở từ trường' : 'Cảnh báo đang hoạt động'}
                  </p>

                  {activeAlerts.length === 0 ? (
                    <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '32px 20px', textAlign: 'center', fontSize: 13, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif' }}>
                      {persona === 'parent' ? 'Chưa có nhắc nhở mới' : 'Không có cảnh báo'}
                    </div>
                  ) : activeAlerts.map(a => {
                    const c = a.level === 'high' ? '#f87171' : a.level === 'medium' ? '#fbbf24' : '#4ade80'
                    return (
                      <div key={a.id} style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '14px 16px', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: c, flexShrink: 0, marginTop: 4 }} />
                        <div style={{ flex: 1 }}>
                          <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.75)', lineHeight: 1.5, fontFamily: 'DM Sans, sans-serif' }}>{a.message}</p>
                          <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', fontFamily: 'JetBrains Mono, monospace', marginTop: 4 }}>
                            {new Date(a.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                        <button onClick={() => dismiss(a.id)} style={{ fontSize: 14, color: 'rgba(255,255,255,0.25)', flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                      </div>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </div>

          {/* Bottom nav */}
          <div style={{ display: 'flex', borderTop: '1px solid rgba(255,255,255,0.06)', padding: '8px 0 20px', background: 'rgba(6,12,7,0.95)', backdropFilter: 'blur(12px)', flexShrink: 0 }}>
            <AnimatePresence mode="wait">
              {TABS.map(t => {
                const active = tab === t.id
                const badge = t.id === 'alerts' && activeAlerts.length > 0
                return (
                  <button key={`${persona}-${t.id}`} onClick={() => setTab(t.id)}
                    style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '6px 0', color: active ? '#4ade80' : 'rgba(255,255,255,0.3)', position: 'relative', transition: 'color 0.2s', background: 'none', border: 'none', cursor: 'pointer' }}>
                    {badge && <span style={{ position: 'absolute', top: 2, right: '28%', width: 7, height: 7, borderRadius: '50%', background: '#f87171' }} />}
                    {active && (
                      <motion.span
                        layoutId={`tab-indicator-${persona}`}
                        style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: 20, height: 2, borderRadius: 1, background: '#4ade80' }}
                      />
                    )}
                    <t.Icon />
                    <span style={{ fontSize: 9, fontFamily: 'DM Sans, sans-serif', fontWeight: 500, letterSpacing: '0.04em' }}>{t.label}</span>
                  </button>
                )
              })}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
