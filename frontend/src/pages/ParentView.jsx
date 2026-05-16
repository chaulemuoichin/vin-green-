import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'

const HANOI_AVG = 45

function basePm25(hour) {
  const morning   = 105 * Math.exp(-0.5 * ((hour - 7.5)  / 0.5) ** 2)
  const afternoon = 95  * Math.exp(-0.5 * ((hour - 16.0) / 0.5) ** 2)
  return Math.max(8, Math.round(30 + morning + afternoon))
}

const DAILY_PATTERN = [
  { time: '06:00', pm25: 28 }, { time: '06:30', pm25: 36 },
  { time: '07:00', pm25: 68 }, { time: '07:15', pm25: 98 },
  { time: '07:30', pm25: 128 }, { time: '07:45', pm25: 134 },
  { time: '08:00', pm25: 118 }, { time: '08:30', pm25: 82 },
  { time: '09:00', pm25: 48 }, { time: '10:00', pm25: 35 },
  { time: '12:00', pm25: 32 }, { time: '13:00', pm25: 34 },
  { time: '14:00', pm25: 38 }, { time: '15:00', pm25: 52 },
  { time: '15:30', pm25: 78 }, { time: '15:45', pm25: 102 },
  { time: '16:00', pm25: 122 }, { time: '16:30', pm25: 118 },
  { time: '17:00', pm25: 88 }, { time: '17:30', pm25: 52 },
  { time: '18:00', pm25: 34 }, { time: '18:30', pm25: 28 },
]

function getSafeWindow() {
  const now = new Date()
  const total = now.getHours() * 60 + now.getMinutes()
  if (total < 15 * 60 + 30) return { time: '15:30', safe: true,  note: 'Đón trước cao điểm — không khí còn tốt' }
  if (total < 17 * 60)      return { time: '17:00', safe: false, note: 'Đang cao điểm ô nhiễm — nên đợi thêm' }
  return { time: 'Ngay bây giờ', safe: true, note: 'Không khí đã cải thiện sau cao điểm' }
}

const HEALTH = {
  low:    { status: 'AN TOÀN',     tips: ['Mở cửa sổ xe thông thoáng', 'Trẻ vận động ngoài trời bình thường', 'Không cần biện pháp đặc biệt'] },
  medium: { status: 'CẦN LƯU Ý',  tips: ['Đóng kính xe khi đón con', 'Không để xe nổ máy trước cổng', 'Đón nhanh và vào trong ngay', 'Trẻ nhạy cảm hạn chế ra ngoài'] },
  high:   { status: 'NGUY HIỂM',  tips: ['Đeo khẩu trang cho trẻ', 'Đón thật nhanh, vào xe ngay', 'Bật lọc không khí trong xe', 'Báo giáo viên nếu trẻ có triệu chứng'] },
}

const fade = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

function PatternTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const v = payload[0].value
  const c = v < 35 ? '#4ade80' : v < 75 ? '#fbbf24' : '#f87171'
  return (
    <div style={{ background: '#0a1409', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '7px 12px' }}>
      <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: 10, marginBottom: 4, fontFamily: 'DM Sans, sans-serif' }}>{label}</p>
      <p style={{ color: c, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, fontSize: 14 }}>{v} µg/m³</p>
    </div>
  )
}

export default function ParentView({ pm25, risk, alerts }) {
  const safeWin = getSafeWindow()
  const health  = HEALTH[risk] || HEALTH.low
  const riskColor = risk === 'high' ? '#f87171' : risk === 'medium' ? '#fbbf24' : '#4ade80'
  const active  = alerts.filter(a => !a.dismissed)
  const [copied, setCopied] = useState(false)

  const handleShare = () => {
    const time = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    const date = new Date().toLocaleDateString('vi-VN')
    const riskLabel = { low: 'AN TOÀN', medium: 'CẦN LƯU Ý', high: 'NGUY HIỂM' }[risk] || 'AN TOÀN'
    const text = `🛡️ SchoolShield — THCS Nguyễn Trãi\n${time} · ${date}\nPM2.5: ${pm25.toFixed(1)} µg/m³\nMức độ: ${riskLabel}\n${health.tips[0]}`
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    })
  }

  return (
    <motion.div
      initial="hidden" animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: 0.07 } } }}
    >
      {/* Heading */}
      <motion.div variants={fade} className="mb-10">
        <h1 style={{ fontFamily: 'Be Vietnam Pro, sans-serif', fontWeight: 800, fontSize: 'clamp(28px,3vw,46px)', color: 'rgba(255,255,255,0.9)', lineHeight: 1.15 }}>
          Bảo vệ con bạn
        </h1>
        <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.32)', marginTop: 6, fontFamily: 'DM Sans, sans-serif' }}>
          THCS Nguyễn Trãi · Hoan Kiếm · Cập nhật mỗi 5 giây
        </p>
      </motion.div>

      {/* Hero row */}
      <motion.div variants={fade} className="grid gap-4 mb-4" style={{ gridTemplateColumns: '1fr 1fr' }}>

        {/* Status card */}
        <div className="surface p-8 flex flex-col justify-between" style={{ minHeight: 240, borderColor: `${riskColor}28` }}>
          <span className="label">Tình trạng không khí</span>
          <motion.p
            key={risk}
            initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            style={{ fontFamily: 'Be Vietnam Pro, sans-serif', fontWeight: 800, fontSize: 'clamp(36px,4vw,54px)', color: riskColor, lineHeight: 1.05, margin: '16px 0 10px' }}
          >
            {health.status}
          </motion.p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 32, fontWeight: 600, color: riskColor }}>{pm25.toFixed(1)}</span>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif' }}>µg/m³ PM2.5</span>
          </div>
          <p style={{ fontSize: 11, color: riskColor, marginBottom: 14, fontFamily: 'DM Sans, sans-serif' }}>
            {pm25 > HANOI_AVG
              ? `Cao hơn ${Math.round((pm25 - HANOI_AVG) / HANOI_AVG * 100)}% so với TB Hà Nội`
              : `Thấp hơn ${Math.round((HANOI_AVG - pm25) / HANOI_AVG * 100)}% so với TB Hà Nội`}
          </p>
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <button
              onClick={handleShare}
              style={{
                fontFamily: 'DM Sans, sans-serif', fontSize: 12, fontWeight: 500,
                padding: '6px 14px', borderRadius: 8, cursor: 'pointer',
                background: 'transparent', border: `1px solid ${riskColor}55`,
                color: riskColor, transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = `${riskColor}15` }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
            >
              Chia sẻ qua Zalo
            </button>
            <AnimatePresence>
              {copied && (
                <motion.span
                  initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.18 }}
                  style={{
                    position: 'absolute', left: '50%', transform: 'translateX(-50%)',
                    bottom: -26, whiteSpace: 'nowrap',
                    fontSize: 11, color: '#4ade80', fontFamily: 'DM Sans, sans-serif',
                  }}
                >
                  Đã sao chép! ✓
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Best pickup time card */}
        <div className="surface p-8 flex flex-col justify-between" style={{ minHeight: 240 }}>
          <span className="label">Giờ đón tốt nhất chiều nay</span>
          <div style={{ textAlign: 'center', padding: '12px 0' }}>
            <motion.p
              style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, fontSize: 'clamp(44px,5vw,64px)', color: safeWin.safe ? '#4ade80' : '#fbbf24', lineHeight: 1 }}
              animate={{ opacity: [0.75, 1, 0.75] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              {safeWin.time}
            </motion.p>
            <p style={{ fontFamily: 'DM Sans, sans-serif', fontSize: 13, color: 'rgba(255,255,255,0.4)', marginTop: 10, lineHeight: 1.5 }}>
              {safeWin.note}
            </p>
            {(() => {
              const now = new Date()
              const bars = [1, 2, 3].map(h => {
                const ft = new Date(now.getTime() + h * 3_600_000)
                const val = basePm25(ft.getHours() + ft.getMinutes() / 60)
                const color = val < 35 ? '#4ade80' : val < 75 ? '#fbbf24' : '#f87171'
                return { label: `${h} giờ`, val, color, barH: Math.max(3, Math.round(val / 150 * 40)) }
              })
              const COL = 30, GAP = 12
              return (
                <div style={{ marginTop: 14, display: 'inline-flex', flexDirection: 'column', gap: 3 }}>
                  <div style={{ display: 'flex', gap: GAP }}>
                    {bars.map(b => (
                      <div key={b.label} style={{ width: COL, textAlign: 'center' }}>
                        <span style={{ fontSize: 9, color: b.color, fontFamily: 'JetBrains Mono, monospace' }}>{b.val}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: GAP, alignItems: 'flex-end', height: 40 }}>
                    {bars.map(b => (
                      <div key={b.label} style={{ width: COL, display: 'flex', justifyContent: 'center' }}>
                        <div style={{ width: 18, height: b.barH, background: b.color, borderRadius: 3, opacity: 0.85 }} />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: GAP }}>
                    {bars.map(b => (
                      <div key={b.label} style={{ width: COL, textAlign: 'center' }}>
                        <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', fontFamily: 'DM Sans, sans-serif' }}>{b.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })()}
          </div>
          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', fontFamily: 'DM Sans, sans-serif', textAlign: 'center', lineHeight: 1.6 }}>
            Cao điểm ô nhiễm chiều: 15:30 – 17:00
          </p>
        </div>
      </motion.div>

      {/* Tips row */}
      <motion.div variants={fade} className="surface p-7 mb-4">
        <span className="label mb-4 block">Khuyến nghị cho phụ huynh</span>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          {health.tips.map((tip, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <span style={{ color: riskColor, fontSize: 14, flexShrink: 0, marginTop: 1 }}>→</span>
              <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.62)', fontFamily: 'DM Sans, sans-serif', lineHeight: 1.55 }}>{tip}</p>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Daily pattern chart */}
      <motion.div variants={fade} className="surface p-7 mb-4">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <span className="label">Mô hình ô nhiễm điển hình trong ngày</span>
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.22)', fontFamily: 'DM Sans, sans-serif' }}>Dựa trên dữ liệu cổng trường</span>
        </div>
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart data={DAILY_PATTERN} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
            <defs>
              {/* Vertical gradient — top=red (high PM2.5), 50%=yellow, 77%=green, bottom=green */}
              <linearGradient id="pStroke" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#f87171" />
                <stop offset="50%"  stopColor="#fbbf24" />
                <stop offset="77%"  stopColor="#4ade80" />
                <stop offset="100%" stopColor="#4ade80" />
              </linearGradient>
              <linearGradient id="pFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#f87171" stopOpacity="0.18" />
                <stop offset="50%"  stopColor="#fbbf24" stopOpacity="0.10" />
                <stop offset="77%"  stopColor="#4ade80" stopOpacity="0.07" />
                <stop offset="100%" stopColor="#4ade80" stopOpacity="0" />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickLine={false} axisLine={false} interval={2} />
            <YAxis domain={[0, 150]} hide />
            <Tooltip content={<PatternTip />} cursor={{ stroke: 'rgba(255,255,255,0.07)', strokeWidth: 1 }} />
            <ReferenceLine y={35} stroke="#4ade80" strokeDasharray="3 5" strokeOpacity={0.25} />
            <ReferenceLine y={75} stroke="#f87171" strokeDasharray="3 5" strokeOpacity={0.25} />
            <Area type="monotone" dataKey="pm25" stroke="url(#pStroke)" strokeWidth={2}
              fill="url(#pFill)" dot={false}
              activeDot={{ r: 3, fill: '#fbbf24', stroke: '#060c07', strokeWidth: 2 }} />
          </AreaChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 20, marginTop: 10 }}>
          {[['#4ade80', '< 35 · An toàn'], ['#fbbf24', '35–75 · Cần lưu ý'], ['#f87171', '> 75 · Nguy hiểm']].map(([c, l]) => (
            <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'rgba(255,255,255,0.28)', fontFamily: 'DM Sans, sans-serif' }}>
              <span style={{ width: 14, height: 1.5, background: c, opacity: 0.7, display: 'inline-block', borderRadius: 1 }} />
              {l}
            </span>
          ))}
        </div>
      </motion.div>

      {/* Active alerts */}
      {active.length > 0 && (
        <motion.div variants={fade} className="surface p-7">
          <span className="label mb-4 block">Thông báo đang hoạt động</span>
          {active.map(a => {
            const c = a.level === 'high' ? '#f87171' : a.level === 'medium' ? '#fbbf24' : '#4ade80'
            return (
              <div key={a.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <motion.span style={{ width: 6, height: 6, borderRadius: '50%', background: c, flexShrink: 0, marginTop: 4, display: 'block' }}
                  animate={{ opacity: [0.5, 1, 0.5] }} transition={{ duration: 1.8, repeat: Infinity }} />
                <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.62)', flex: 1, lineHeight: 1.55, fontFamily: 'DM Sans, sans-serif' }}>{a.message}</p>
              </div>
            )
          })}
        </motion.div>
      )}
    </motion.div>
  )
}
