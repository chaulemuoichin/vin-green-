import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAQI } from '../hooks/useAQI'
import { useAlerts } from '../hooks/useAlerts'
import { usePersona } from '../context/PersonaContext'
import AQIGauge from '../components/AQIGauge'
import RiskBadge from '../components/RiskBadge'
import AlertBanner from '../components/AlertBanner'
import TrendChart from '../components/TrendChart'
import MapPin from '../components/MapPin'
import IdlingTicker from '../components/IdlingTicker'
import ParticleField from '../components/ParticleField'
import ActionChecklist from '../components/ActionChecklist'
import Analytics from './Analytics'
import ParentView from './ParentView'

/* ── Live clock ─────────────────────────────────────────────── */
function Clock() {
  const [t, setT] = useState(new Date())
  useEffect(() => { const id = setInterval(() => setT(new Date()), 1000); return () => clearInterval(id) }, [])
  return (
    <span className="data-value" style={{ fontSize: 12, color: 'rgba(255,255,255,0.25)' }}>
      {t.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

/* ── Persona switcher ───────────────────────────────────────── */
function PersonaToggle() {
  const { persona, setPersona } = usePersona()
  return (
    <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 3, gap: 2 }}>
      {[['parent', 'Phụ huynh'], ['school', 'Nhà trường']].map(([id, label]) => (
        <button key={id} onClick={() => setPersona(id)}
          style={{
            fontFamily: 'DM Sans, sans-serif', fontSize: 12, fontWeight: 500,
            padding: '5px 14px', borderRadius: 7, border: 'none', cursor: 'pointer',
            background: persona === id ? 'rgba(255,255,255,0.09)' : 'transparent',
            color: persona === id ? 'rgba(255,255,255,0.88)' : 'rgba(255,255,255,0.3)',
            transition: 'all 0.2s',
          }}
        >{label}</button>
      ))}
    </div>
  )
}

/* ── Small stat card ────────────────────────────────────────── */
const fade = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

function Stat({ label, value, unit, color = 'rgba(255,255,255,0.88)' }) {
  return (
    <motion.div variants={fade} className="surface p-6 flex flex-col gap-2">
      <span className="label">{label}</span>
      <p className="data-value leading-none" style={{ fontSize: 36, color }}>
        {value}
        {unit && <span style={{ fontSize: 14, color: 'rgba(255,255,255,0.3)', fontWeight: 400, marginLeft: 6, fontFamily: 'DM Sans, sans-serif' }}>{unit}</span>}
      </p>
    </motion.div>
  )
}

/* ── Expandable alert row ───────────────────────────────────── */
function AlertRow({ alert, expanded, onToggle }) {
  const c = alert.level === 'high' ? '#f87171' : alert.level === 'medium' ? '#fbbf24' : '#4ade80'
  const levelLabel = { high: 'CAO', medium: 'TRUNG BÌNH', low: 'THẤP' }[alert.level] || 'THẤP'

  return (
    <div>
      <div
        className="flex items-start gap-4 py-4 cursor-pointer select-none"
        style={{ borderBottom: expanded ? 'none' : '1px solid rgba(255,255,255,0.05)' }}
        onClick={onToggle}
      >
        <span className="mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: c }} />
        <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', flex: 1, lineHeight: 1.5, fontFamily: 'DM Sans, sans-serif' }}>{alert.message}</p>
        {alert.count > 1 ? (
          <span style={{ fontSize: 11, color: '#fbbf24', fontFamily: 'DM Sans, sans-serif', background: 'rgba(251,191,36,0.12)', padding: '2px 6px', borderRadius: 6, flexShrink: 0 }}>
            {alert.count}×
          </span>
        ) : (
          <span className="data-value flex-shrink-0" style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)' }}>
            {new Date(alert.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
        <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 10, transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}>▾</span>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: 'hidden', borderBottom: '1px solid rgba(255,255,255,0.05)' }}
          >
            <div style={{ padding: '8px 0 16px 22px', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              {[
                ['Mức độ', <span key="l" style={{ fontSize: 12, fontWeight: 600, color: c, letterSpacing: '0.06em' }}>{levelLabel}</span>],
                ['Thời gian', <span key="t" className="data-value" style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{new Date(alert.created_at).toLocaleString('vi-VN')}</span>],
                ['Trạng thái', <span key="s" style={{ fontSize: 12, color: alert.dismissed ? '#4ade80' : '#fbbf24' }}>{alert.dismissed ? 'Đã xử lý' : 'Đang hoạt động'}</span>],
              ].map(([title, content]) => (
                <div key={title} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span className="label" style={{ fontSize: 10 }}>{title}</span>
                  {content}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ── Alert grouping ─────────────────────────────────────────── */
function groupAlerts(alerts) {
  if (!alerts.length) return []
  const sorted = [...alerts].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
  const groups = []
  for (const alert of sorted) {
    const prev = groups[groups.length - 1]
    const levelLabel = { high: 'CAO', medium: 'TRUNG BÌNH', low: 'THẤP' }[alert.level] || 'THẤP'
    if (
      prev &&
      prev.level === alert.level &&
      new Date(alert.created_at) - new Date(prev._lastTime) <= 10 * 60 * 1000
    ) {
      prev.count++
      prev._lastTime = alert.created_at
      const endTime = new Date(alert.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
      prev.message = `${prev.count} lần ${levelLabel} liên tục — ${prev.startTime} đến ${endTime}`
    } else {
      groups.push({
        ...alert,
        count: 1,
        startTime: new Date(alert.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        _lastTime: alert.created_at,
      })
    }
  }
  return groups
}

/* ── Tab nav ────────────────────────────────────────────────── */
const TABS = [
  { id: 'dashboard', label: 'Bảng điều khiển' },
  { id: 'analytics', label: 'Phân tích' },
]

/* ── Main ───────────────────────────────────────────────────── */
export default function Dashboard() {
  const { current, history } = useAQI()
  const { alerts, dismiss } = useAlerts()
  const nav = useNavigate()
  const { persona } = usePersona()
  const [tab, setTab] = useState('dashboard')
  const [expandedAlert, setExpandedAlert] = useState(null)
  const [soundEnabled, setSoundEnabled] = useState(false)
  const prevRiskRef = useRef(null)
  const alertLogRef = useRef(null)

  const pm25      = current?.pm25 ?? 0
  const risk      = current?.risk ?? 'low'
  const idling    = current?.idling_count ?? 0
  const active    = alerts.filter(a => !a.dismissed)
  const riskColor = risk === 'high' ? '#f87171' : risk === 'medium' ? '#fbbf24' : '#4ade80'
  const exposureMinutes = history.filter(h => h.pm25 >= 35).length
  const groupedAlerts = groupAlerts(alerts)

  useEffect(() => { document.body.dataset.risk = risk }, [risk])

  useEffect(() => {
    if (risk === 'high' && soundEnabled && prevRiskRef.current !== 'high') {
      try {
        const ctx = new AudioContext()
        const osc = ctx.createOscillator()
        osc.frequency.value = 520
        osc.connect(ctx.destination)
        osc.start()
        osc.stop(ctx.currentTime + 0.18)
      } catch (_) {}
    }
    prevRiskRef.current = risk
  }, [risk, soundEnabled])

  useEffect(() => {
    if (risk === 'high' && alerts.length > 0) {
      setExpandedAlert(alerts[0].id)
      alertLogRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [risk])

  return (
    <div className="min-h-screen flex flex-col">

      {/* Header */}
      <header style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(16px)', background: 'rgba(6,12,7,0.8)', position: 'sticky', top: 0, zIndex: 40 }}>
        <div className="max-w-7xl mx-auto px-8 h-14 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <svg width="22" height="22" viewBox="0 0 64 64" fill="none">
              <path d="M32 4L8 14v18c0 14 10.5 25.5 24 28 13.5-2.5 24-14 24-28V14L32 4z"
                fill="rgba(74,222,128,0.15)" stroke="#4ade80" strokeWidth="1.5"/>
              <path d="M32 44s-12-7-12-18c0-5 4-9 8-10 0 4 2 8 6 11 4-3 6-7 6-11 4 1 8 5 8 10 0 11-16 18-16 18z"
                fill="#4ade80"/>
            </svg>
            <span style={{ fontFamily: 'DM Sans, sans-serif', fontWeight: 600, fontSize: 15, letterSpacing: '-0.01em' }}>
              <span style={{ color: 'rgba(255,255,255,0.9)' }}>School</span>
              <span style={{ color: '#4ade80' }}>Shield</span>
            </span>
            <span style={{ height: 16, width: 1, background: 'rgba(255,255,255,0.1)', margin: '0 4px' }} />
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>
              THCS Nguyễn Trãi
            </span>
          </div>

          {/* Right */}
          <div className="flex items-center gap-4">
            <PersonaToggle />
            <div className="flex items-center gap-2">
              <motion.span className="w-1.5 h-1.5 rounded-full"
                style={{ background: '#4ade80' }}
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>Đang theo dõi</span>
            </div>
            <Clock />
            <button
              onClick={() => setSoundEnabled(v => !v)}
              title={soundEnabled ? 'Tắt âm thanh cảnh báo' : 'Bật âm thanh cảnh báo'}
              style={{ fontSize: 14, background: 'none', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '4px 8px', cursor: 'pointer', lineHeight: 1, transition: 'all 0.2s', color: soundEnabled ? '#fbbf24' : 'rgba(255,255,255,0.25)', borderColor: soundEnabled ? 'rgba(251,191,36,0.3)' : 'rgba(255,255,255,0.08)' }}
            >
              {soundEnabled ? '🔔' : '🔕'}
            </button>
            <button onClick={() => nav('/mobile')}
              style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)', fontFamily: 'DM Sans, sans-serif', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '4px 10px', transition: 'all 0.2s', background: 'none', cursor: 'pointer' }}
              onMouseEnter={e => { e.currentTarget.style.color = 'rgba(255,255,255,0.6)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)' }}
              onMouseLeave={e => { e.currentTarget.style.color = 'rgba(255,255,255,0.25)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}
            >
              Mobile →
            </button>
          </div>
        </div>

        {/* Alert banner — school view only */}
        {persona === 'school' && <AlertBanner alerts={alerts} onDismiss={dismiss} />}

        {/* Tab strip — school view only */}
        {persona === 'school' && (
          <div className="max-w-7xl mx-auto px-8 flex items-center gap-1">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{
                  fontFamily: 'DM Sans, sans-serif', fontSize: 13, fontWeight: 500,
                  padding: '10px 16px', background: 'none', border: 'none', cursor: 'pointer',
                  color: tab === t.id ? 'rgba(255,255,255,0.88)' : 'rgba(255,255,255,0.35)',
                  borderBottom: tab === t.id ? '1.5px solid rgba(255,255,255,0.7)' : '1.5px solid transparent',
                  transition: 'all 0.2s',
                }}
              >{t.label}</button>
            ))}
          </div>
        )}
      </header>

      {/* Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-8 py-10">
        <AnimatePresence mode="wait">

          {/* Parent view */}
          {persona === 'parent' && (
            <motion.div key="parent" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
              <ParentView pm25={pm25} risk={risk} alerts={alerts} history={history} />
            </motion.div>
          )}

          {/* School — analytics tab */}
          {persona === 'school' && tab === 'analytics' && (
            <motion.div key="analytics" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
              <Analytics />
            </motion.div>
          )}

          {/* School — dashboard tab */}
          {persona === 'school' && tab === 'dashboard' && (
            <motion.div key="dashboard"
              initial="hidden" animate="show" exit={{ opacity: 0 }}
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.07 } } }}
            >
              {/* Page heading */}
              <motion.div variants={fade} className="mb-10">
                <h1 style={{
                  fontFamily: 'Be Vietnam Pro, sans-serif', fontSize: 'clamp(32px, 3.5vw, 52px)',
                  fontWeight: 800, color: 'rgba(255,255,255,0.88)', lineHeight: 1.15,
                  letterSpacing: '-0.01em',
                }}>
                  Không khí cổng trường
                </h1>
                <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.35)', marginTop: 6, fontFamily: 'DM Sans, sans-serif', letterSpacing: '0.02em' }}>
                  Hoan Kiếm · Hà Nội · Cổng chính · Thời gian thực
                </p>
              </motion.div>

              {/* HERO: Gauge + Map */}
              <motion.div variants={fade} className="grid gap-4 mb-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="surface p-8 flex flex-col items-center justify-center gap-6" style={{ minHeight: 340, position: 'relative', overflow: 'hidden' }}>
                  <ParticleField pm25={pm25} />
                  <AQIGauge pm25={pm25} />
                  <RiskBadge risk={risk} />
                </div>
                <div className="surface overflow-hidden" style={{ minHeight: 340 }}>
                  <div style={{ height: '100%', minHeight: 340 }}>
                    <MapPin pm25={pm25} />
                  </div>
                </div>
              </motion.div>

              {/* Action checklist — appears only when risk = high */}
              <ActionChecklist risk={risk} />

              {/* Metric row */}
              <motion.div variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06 } } }}
                className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-4"
              >
                <Stat label="PM2.5 hiện tại" value={pm25.toFixed(1)} unit="µg/m³" color={riskColor} />
                <IdlingTicker idling={idling} risk={risk} />
                <Stat label="Cảnh báo đang hoạt động" value={active.length}
                  color={active.length > 0 ? '#f87171' : 'rgba(255,255,255,0.88)'} />
                <Stat label="Tiếp xúc cao hôm nay" value={exposureMinutes} unit="phút" />
              </motion.div>

              {/* Trend chart */}
              <motion.div variants={fade} className="mb-4">
                <TrendChart data={history} />
              </motion.div>

              {/* Alert log */}
              <motion.div ref={alertLogRef} variants={fade} className="surface p-7">
                <span className="label mb-1 block">Nhật ký cảnh báo</span>
                <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', fontFamily: 'DM Sans, sans-serif', marginBottom: 4 }}>
                  Nhấn vào hàng để xem chi tiết
                </p>
                {groupedAlerts.length === 0 ? (
                  <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.25)', marginTop: 16, fontFamily: 'DM Sans, sans-serif' }}>Không có cảnh báo nào.</p>
                ) : groupedAlerts.map(a => (
                  <AlertRow
                    key={a.id}
                    alert={a}
                    expanded={expandedAlert === a.id}
                    onToggle={() => setExpandedAlert(expandedAlert === a.id ? null : a.id)}
                  />
                ))}
              </motion.div>
            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  )
}
