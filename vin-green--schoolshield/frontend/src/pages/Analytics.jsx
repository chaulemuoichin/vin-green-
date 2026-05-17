import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'

const weeklyData = [
  { week: 'Tuần 1', truoc: 68, sau: 45 },
  { week: 'Tuần 2', truoc: 74, sau: 38 },
  { week: 'Tuần 3', truoc: 71, sau: 33 },
  { week: 'Tuần 4', truoc: 65, sau: 28 },
]

const alertHistory = [
  { date: '13/05', count: 5, avg_pm25: 82 },
  { date: '14/05', count: 3, avg_pm25: 69 },
  { date: '15/05', count: 7, avg_pm25: 91 },
  { date: '16/05', count: 2, avg_pm25: 54 },
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#0a1409', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: '8px 14px' }}>
      <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginBottom: 6, fontFamily: 'DM Sans, sans-serif' }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.fill, fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 600 }}>
          {p.name === 'truoc' ? 'Trước' : 'Sau'}: {p.value} µg/m³
        </p>
      ))}
    </div>
  )
}

export default function Analytics() {
  const reduction = Math.round(((weeklyData[0].truoc - weeklyData[3].sau) / weeklyData[0].truoc) * 100)

  return (
    <div style={{ paddingBottom: 40 }}>
      {/* KPI strip */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Giảm phơi nhiễm', value: `${reduction}%`, color: '#4ade80' },
          { label: 'Tổng cảnh báo', value: '17', color: '#f87171' },
          { label: 'Xe nổ máy ngăn chặn', value: '143', color: '#fbbf24' },
          { label: 'Ngày theo dõi', value: '28', color: 'rgba(255,255,255,0.88)' },
        ].map(kpi => (
          <div key={kpi.label} className="surface p-6 flex flex-col gap-2">
            <span className="label">{kpi.label}</span>
            <p className="data-value" style={{ fontSize: 36, color: kpi.color, lineHeight: 1 }}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Before/after chart */}
      <div className="surface p-7 mb-4">
        <span className="label mb-5 block">PM2.5 trung bình — Trước và Sau can thiệp (µg/m³)</span>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={weeklyData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="week" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11, fontFamily: 'DM Sans, sans-serif' }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              formatter={v => <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', fontFamily: 'DM Sans, sans-serif' }}>{v === 'truoc' ? 'Trước can thiệp' : 'Sau can thiệp'}</span>}
              wrapperStyle={{ paddingTop: 12 }}
            />
            <Bar dataKey="truoc" name="truoc" fill="#f87171" fillOpacity={0.65} radius={[4, 4, 0, 0]} />
            <Bar dataKey="sau"   name="sau"   fill="#4ade80" fillOpacity={0.65} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Alert history table */}
      <div className="surface p-7">
        <span className="label mb-5 block">Lịch sử cảnh báo theo ngày</span>
        <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Ngày', 'Số cảnh báo', 'PM2.5 TB (µg/m³)', 'Đánh giá'].map(h => (
                <th key={h} style={{ textAlign: 'left', paddingBottom: 12 }}>
                  <span className="label">{h}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {alertHistory.map(row => {
              const r = row.avg_pm25 < 35 ? 'low' : row.avg_pm25 < 75 ? 'medium' : 'high'
              const label = { low: 'THẤP', medium: 'TRUNG BÌNH', high: 'CAO' }[r]
              const color = { low: '#4ade80', medium: '#fbbf24', high: '#f87171' }[r]
              return (
                <tr key={row.date} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px 0', fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>{row.date}</td>
                  <td style={{ padding: '12px 0', color: 'rgba(255,255,255,0.75)' }}>{row.count} lần</td>
                  <td style={{ padding: '12px 0', fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.75)', fontSize: 12 }}>{row.avg_pm25}</td>
                  <td style={{ padding: '12px 0', fontWeight: 600, fontSize: 11, letterSpacing: '0.06em', color }}>{label}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
