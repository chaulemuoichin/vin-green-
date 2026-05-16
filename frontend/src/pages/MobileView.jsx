import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAQI } from '../hooks/useAQI'
import { useAlerts } from '../hooks/useAlerts'
import { usePersona } from '../context/PersonaContext'
import AQIGauge from '../components/AQIGauge'
import RiskBadge from '../components/RiskBadge'
import TrendChart from '../components/TrendChart'
import MapPin from '../components/MapPin'

const TABS = [
  { id: 'home',   label: 'Trang chủ', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg> },
  { id: 'map',    label: 'Bản đồ',    icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg> },
  { id: 'chart',  label: 'Xu hướng',  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> },
  { id: 'alerts', label: 'Cảnh báo',  icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> },
]

/* Safe pickup time helper */
function getSafeWindow() {
  const now = new Date()
  const total = now.getHours() * 60 + now.getMinutes()
  if (total < 7 * 60 + 15)  return { time: '07:15', safe: true,  note: 'Trước cao điểm sáng' }
  if (total < 8 * 60 + 20)  return { time: '08:20', safe: false, note: 'Đang cao điểm — chờ thêm' }
  if (total < 15 * 60 + 40) return { time: '15:40', safe: true,  note: 'Trước cao điểm chiều' }
  if (total < 17 * 60)      return { time: '17:00', safe: false, note: 'Đang cao điểm — chờ thêm' }
  return { time: 'Ngay bây giờ', safe: true, note: 'Không khí đã cải thiện' }
}

const HEALTH = {
  low:    { status: 'AN TOÀN',    tips: ['Mở cửa sổ xe', 'Trẻ ra ngoài bình thường'] },
  medium: { status: 'CẦN LƯU Ý', tips: ['Đóng kính xe khi đón', 'Không để xe nổ máy', 'Đón nhanh rồi vào xe'] },
  high:   { status: 'NGUY HIỂM', tips: ['Đeo khẩu trang cho trẻ', 'Đón thật nhanh', 'Bật lọc không khí xe'] },
}

export default function MobileView() {
  const [tab, setTab] = useState('home')
  const { current, history } = useAQI()
  const { alerts, dismiss } = useAlerts()
  const { persona, setPersona } = usePersona()
  const nav = useNavigate()

  const pm25   = current?.pm25 ?? 0
  const risk   = current?.risk ?? 'low'
  const idling = current?.idling_count ?? 0
  const riskColor = risk === 'high' ? '#f87171' : risk === 'medium' ? '#fbbf24' : '#4ade80'
  const activeAlerts = alerts.filter(a => !a.dismissed)
  const safeWin = getSafeWindow()
  const health  = HEALTH[risk] || HEALTH.low

  useEffect(() => { document.body.dataset.risk = risk }, [risk])

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
        <div style={{
          position: 'absolute', inset: 0, borderRadius: 52,
          background: '#111', zIndex: 10, pointerEvents: 'none',
          boxShadow: '0 0 0 1px rgba(255,255,255,0.07), 0 40px 80px rgba(0,0,0,0.7), inset 0 0 0 1px rgba(255,255,255,0.04)',
        }} />
        {/* Side buttons */}
        {[{ l: true, t: 112, h: 40 }, { l: true, t: 176, h: 64 }, { l: true, t: 256, h: 64 }, { l: false, t: 160, h: 80 }].map((b, i) => (
          <div key={i} style={{ position: 'absolute', [b.l ? 'left' : 'right']: -3, top: b.t, width: 3, height: b.h, borderRadius: b.l ? '2px 0 0 2px' : '0 2px 2px 0', background: 'rgba(255,255,255,0.08)' }} />
        ))}

        {/* Screen */}
        <div style={{ position: 'absolute', inset: 3, borderRadius: 49, overflow: 'hidden', background: '#060c07', zIndex: 5, display: 'flex', flexDirection: 'column' }}>

          {/* Status bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 28px 8px', flexShrink: 0 }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.8)' }}>
              {new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
            </span>
            <div style={{ width: 100, height: 22, background: '#111', borderRadius: '0 0 14px 14px' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <svg width="13" height="9" viewBox="0 0 13 9" fill="white"><rect x="0" y="3" width="2" height="6" rx=".5" fillOpacity=".4" /><rect x="3" y="2" width="2" height="7" rx=".5" fillOpacity=".6" /><rect x="6" y="0" width="2" height="9" rx=".5" fillOpacity=".8" /><rect x="9" y="0" width="2" height="9" rx=".5" /></svg>
              <div style={{ width: 18, height: 10, borderRadius: 3, border: '1px solid rgba(255,255,255,0.4)', padding: '1px' }}>
                <div style={{ width: '75%', height: '100%', borderRadius: 2, background: 'white' }} />
              </div>
            </div>
          </div>

          {/* App header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg width="18" height="18" viewBox="0 0 64 64" fill="none">
                <path d="M32 4L8 14v18c0 14 10.5 25.5 24 28 13.5-2.5 24-14 24-28V14L32 4z" fill="rgba(74,222,128,0.15)" stroke="#4ade80" strokeWidth="2" />
                <path d="M32 44s-12-7-12-18c0-5 4-9 8-10 0 4 2 8 6 11 4-3 6-7 6-11 4 1 8 5 8 10 0 11-16 18-16 18z" fill="#4ade80" />
              </svg>
              <span style={{ fontFamily: 'DM Sans, sans-serif', fontWeight: 600, fontSize: 14 }}>
                <span style={{ color: 'rgba(255,255,255,0.9)' }}>School</span><span style={{ color: '#4ade80' }}>Shield</span>
              </span>
            </div>
            {/* Mobile persona toggle */}
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: 2, gap: 1 }}>
              {[['parent', 'Phụ huynh'], ['school', 'Trường']].map(([id, label]) => (
                <button key={id} onClick={() => setPersona(id)}
                  style={{
                    fontFamily: 'DM Sans, sans-serif', fontSize: 10, fontWeight: 500,
                    padding: '4px 10px', borderRadius: 6, border: 'none', cursor: 'pointer',
                    background: persona === id ? 'rgba(255,255,255,0.09)' : 'transparent',
                    color: persona === id ? 'rgba(255,255,255,0.88)' : 'rgba(255,255,255,0.3)',
                    transition: 'all 0.2s',
                  }}
                >{label}</button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 0' }}>

            {/* HOME TAB */}
            {tab === 'home' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {persona === 'parent' ? (
                  <>
                    {/* Parent home: status + best time */}
                    <div style={{ background: `rgba(255,255,255,0.025)`, border: `1px solid ${riskColor}25`, borderRadius: 18, padding: '20px 16px' }}>
                      <p style={{ fontFamily: 'DM Sans, sans-serif', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', marginBottom: 10 }}>Tình trạng không khí</p>
                      <motion.p key={risk} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        style={{ fontFamily: 'Be Vietnam Pro, sans-serif', fontWeight: 800, fontSize: 34, color: riskColor, lineHeight: 1, marginBottom: 8 }}>
                        {health.status}
                      </motion.p>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 600, color: riskColor }}>{pm25.toFixed(1)} <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontWeight: 400 }}>µg/m³</span></p>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 18, padding: '20px 16px', textAlign: 'center' }}>
                      <p style={{ fontFamily: 'DM Sans, sans-serif', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', marginBottom: 12 }}>Giờ đón tốt nhất</p>
                      <motion.p style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, fontSize: 44, color: safeWin.safe ? '#4ade80' : '#fbbf24', lineHeight: 1 }}
                        animate={{ opacity: [0.75, 1, 0.75] }} transition={{ duration: 3, repeat: Infinity }}>
                        {safeWin.time}
                      </motion.p>
                      <p style={{ fontFamily: 'DM Sans, sans-serif', fontSize: 12, color: 'rgba(255,255,255,0.4)', marginTop: 8 }}>{safeWin.note}</p>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '14px 16px' }}>
                      <p style={{ fontFamily: 'DM Sans, sans-serif', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', marginBottom: 10 }}>Khuyến nghị</p>
                      {health.tips.map((tip, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
                          <span style={{ color: riskColor, fontSize: 12, flexShrink: 0, marginTop: 1 }}>→</span>
                          <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', fontFamily: 'DM Sans, sans-serif', lineHeight: 1.5 }}>{tip}</p>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <>
                    {/* School home: gauge + stats */}
                    {activeAlerts.length > 0 && (
                      <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 14, padding: '12px 14px', fontSize: 12, color: 'rgba(255,255,255,0.75)', lineHeight: 1.5, fontFamily: 'DM Sans, sans-serif' }}>
                        <span style={{ color: '#f87171', fontWeight: 600 }}>CẢNH BÁO — </span>{activeAlerts[0].message}
                      </div>
                    )}
                    <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 18, padding: '20px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                      <AQIGauge pm25={pm25} />
                      <RiskBadge risk={risk} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      {[
                        { label: 'Xe nổ máy', val: idling, unit: 'xe', color: '#fbbf24' },
                        { label: 'PM2.5', val: pm25.toFixed(1), unit: 'µg/m³', color: riskColor },
                      ].map(s => (
                        <div key={s.label} style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '16px 14px' }}>
                          <p style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', marginBottom: 8 }}>{s.label}</p>
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 28, fontWeight: 600, color: s.color, lineHeight: 1 }}>{s.val}</p>
                          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 4, fontFamily: 'DM Sans, sans-serif' }}>{s.unit}</p>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* MAP TAB — always mounted, shown/hidden via CSS to fix Leaflet remount issue */}
            <div style={{ display: tab === 'map' ? 'block' : 'none', borderRadius: 18, overflow: 'hidden', height: 460, border: '1px solid rgba(255,255,255,0.07)' }}>
              <MapPin pm25={pm25} risk={risk} />
            </div>

            {tab === 'chart' && <TrendChart data={history} />}

            {tab === 'alerts' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <p style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', marginBottom: 4 }}>Cảnh báo đang hoạt động</p>
                {activeAlerts.length === 0 ? (
                  <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '32px 20px', textAlign: 'center', fontSize: 13, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>Không có cảnh báo</div>
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
            )}
          </div>

          {/* Bottom nav */}
          <div style={{ display: 'flex', borderTop: '1px solid rgba(255,255,255,0.06)', padding: '8px 0 20px', background: 'rgba(6,12,7,0.95)', backdropFilter: 'blur(12px)', flexShrink: 0 }}>
            {TABS.map(t => {
              const active = tab === t.id
              const badge = t.id === 'alerts' && activeAlerts.length > 0
              return (
                <button key={t.id} onClick={() => setTab(t.id)}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '6px 0', color: active ? '#4ade80' : 'rgba(255,255,255,0.3)', position: 'relative', transition: 'color 0.2s', background: 'none', border: 'none', cursor: 'pointer' }}>
                  {badge && <span style={{ position: 'absolute', top: 2, right: '28%', width: 7, height: 7, borderRadius: '50%', background: '#f87171' }} />}
                  {t.icon}
                  <span style={{ fontSize: 9, fontFamily: 'DM Sans, sans-serif', fontWeight: 500, letterSpacing: '0.04em' }}>{t.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
