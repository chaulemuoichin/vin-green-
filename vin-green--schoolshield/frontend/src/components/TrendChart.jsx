import { useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, CartesianGrid } from 'recharts'
import HeatmapStrip from './HeatmapStrip'

const fmt = d => d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })

function basePm25(hour) {
  const morning   = 105 * Math.exp(-0.5 * ((hour - 7.5)  / 0.5) ** 2)
  const afternoon = 95  * Math.exp(-0.5 * ((hour - 16.0) / 0.5) ** 2)
  return Math.max(8, Math.round(30 + morning + afternoon))
}

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const actual    = payload.find(p => p.dataKey === 'actual'    && p.value != null)
  const predicted = payload.find(p => p.dataKey === 'predicted' && p.value != null)
  const val = actual?.value ?? predicted?.value
  if (val == null) return null
  const isForecast = !actual && !!predicted
  const c = val < 35 ? '#4ade80' : val < 75 ? '#fbbf24' : '#f87171'
  const riskLabel  = val < 35 ? 'AN TOÀN' : val < 75 ? 'CẦN LƯU Ý' : 'NGUY HIỂM'
  const healthNote = val < 35
    ? 'Không ảnh hưởng sức khỏe'
    : val < 75 ? 'Trẻ nhạy cảm hạn chế ra ngoài'
    : 'Ảnh hưởng xấu cho mọi người'
  return (
    <div style={{ background: '#0a1409', border: '1px solid rgba(255,255,255,0.09)', borderRadius: 12, padding: '10px 14px', maxWidth: 200 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <p style={{ color: 'rgba(255,255,255,0.38)', fontSize: 10, fontFamily: 'DM Sans, sans-serif' }}>{label}</p>
        {isForecast && (
          <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', background: 'rgba(255,255,255,0.06)', borderRadius: 4, padding: '1px 5px', fontFamily: 'DM Sans, sans-serif' }}>
            DỰ BÁO
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 5 }}>
        <p style={{ color: c, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, fontSize: 22 }}>{val}</p>
        <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: 10, fontFamily: 'DM Sans, sans-serif' }}>µg/m³</span>
      </div>
      <p style={{ color: c, fontSize: 10, fontFamily: 'DM Sans, sans-serif', fontWeight: 600, letterSpacing: '0.08em', marginBottom: 4 }}>{riskLabel}</p>
      <p style={{ color: 'rgba(255,255,255,0.32)', fontSize: 10, fontFamily: 'DM Sans, sans-serif', lineHeight: 1.45 }}>{healthNote}</p>
    </div>
  )
}

export default function TrendChart({ data = [] }) {
  const { combined, nowTime } = useMemo(() => {
    const now = new Date()
    const past = data.map(d => ({ time: d.time, actual: d.pm25 }))
    const lastPm25 = data.length > 0
      ? data[data.length - 1].pm25
      : basePm25(now.getHours() + now.getMinutes() / 60)
    const nowLabel = fmt(now)
    const bridge = { time: nowLabel, actual: lastPm25, predicted: lastPm25 }
    const future = Array.from({ length: 30 }, (_, i) => {
      const ft = new Date(now.getTime() + (i + 1) * 60_000)
      return { time: fmt(ft), predicted: basePm25(ft.getHours() + ft.getMinutes() / 60) }
    })
    return { combined: [...past, bridge, ...future], nowTime: nowLabel }
  }, [data])

  return (
    <div className="surface p-7">
      <div className="flex items-center justify-between mb-5">
        <span className="label">30 phút qua · Dự báo 30 phút tới</span>
        <div className="flex items-center gap-5">
          <span className="flex items-center gap-1.5" style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>
            <span style={{ width: 16, height: 1.5, background: '#4ade80', display: 'inline-block', borderRadius: 1, opacity: 0.7 }} />
            Thực tế
          </span>
          <span className="flex items-center gap-1.5" style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>
            <span style={{ width: 16, height: 0, border: 'none', borderTop: '1.5px dashed rgba(74,222,128,0.5)', display: 'inline-block' }} />
            Dự báo
          </span>
        </div>
      </div>
      <HeatmapStrip />
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={combined} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
          <defs>
            <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="#4ade80" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#4ade80" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="predictedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="#4ade80" stopOpacity="0.07" />
              <stop offset="100%" stopColor="#4ade80" stopOpacity="0" />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
            tickLine={false} axisLine={false} interval={9} />
          <YAxis domain={[0, 150]} tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
            tickLine={false} axisLine={false} />
          <Tooltip content={<Tip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
          <ReferenceLine y={35} stroke="#4ade80" strokeDasharray="3 5" strokeOpacity={0.3} />
          <ReferenceLine y={75} stroke="#f87171" strokeDasharray="3 5" strokeOpacity={0.3} />
          <ReferenceLine x={nowTime}
            stroke="rgba(255,255,255,0.2)" strokeWidth={1}
            label={{ value: 'Bây giờ', position: 'insideTopRight', fill: 'rgba(255,255,255,0.22)', fontSize: 9, fontFamily: 'DM Sans, sans-serif' }}
          />
          <Area type="monotone" dataKey="actual" stroke="#4ade80" strokeWidth={1.5}
            fill="url(#actualGrad)" dot={false} connectNulls={false}
            activeDot={{ r: 3, fill: '#4ade80', stroke: '#060c07', strokeWidth: 2 }} />
          <Area type="monotone" dataKey="predicted" stroke="#4ade80" strokeWidth={1.2}
            strokeDasharray="5 4" strokeOpacity={0.5}
            fill="url(#predictedGrad)" dot={false} connectNulls={false}
            activeDot={{ r: 3, fill: '#4ade80', stroke: '#060c07', strokeWidth: 2 }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
