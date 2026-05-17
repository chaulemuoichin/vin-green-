import { useEffect, Fragment } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'

function MapResizer() {
  const map = useMap()
  useEffect(() => {
    const t = setTimeout(() => map.invalidateSize(), 120)
    return () => clearTimeout(t)
  }, [map])
  return null
}

function stationRisk(pm25) {
  return pm25 < 35 ? 'low' : pm25 < 75 ? 'medium' : 'high'
}
const RISK_COLOR  = { low: '#4ade80', medium: '#fbbf24', high: '#f87171' }
const RISK_LABEL  = { low: 'AN TOÀN', medium: 'CẦN LƯU Ý', high: 'NGUY HIỂM' }
const HEALTH_NOTE = {
  low:    'Không ảnh hưởng sức khỏe',
  medium: 'Trẻ nhạy cảm hạn chế ra ngoài',
  high:   'Ảnh hưởng xấu cho mọi người',
}

const STATIONS = [
  { id: 0, label: 'Cổng chính', sublabel: 'Mặt đường chính',  pos: [21.0295, 105.8479], mult: 1.0,  offset: 0,  main: true  },
  { id: 1, label: 'Cổng sau',   sublabel: 'Đường nội bộ',      pos: [21.0285, 105.8479], mult: 0.82, offset: -4, main: false },
  { id: 2, label: 'Tường đông', sublabel: 'Khu dân cư',        pos: [21.0292, 105.8492], mult: 0.88, offset: 2,  main: false },
  { id: 3, label: 'Tường tây',  sublabel: 'Đường Nguyễn Trãi', pos: [21.0298, 105.8466], mult: 1.18, offset: 5,  main: false },
  { id: 4, label: 'Bãi đỗ xe', sublabel: 'Sân trong trường',  pos: [21.0302, 105.8479], mult: 1.1,  offset: 3,  main: false },
]

function makeIcon(color, isMain) {
  const size = isMain ? 14 : 11
  return L.divIcon({
    className: '',
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};box-shadow:0 0 0 3px rgba(255,255,255,0.08),0 0 14px ${color}90;border:2px solid rgba(0,0,0,0.45);"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

export default function MapPin({ pm25 = 0 }) {
  const mainPm25 = Math.max(8, Math.round(pm25))

  return (
    <MapContainer
      center={[21.0293, 105.8479]}
      zoom={18}
      style={{ height: '100%', width: '100%' }}
      zoomControl={true}
      attributionControl={false}
      scrollWheelZoom={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        keepBuffer={8}
        updateWhenIdle={false}
        maxZoom={19}
        minZoom={13}
      />

      {STATIONS.map(s => {
        const sPm25  = Math.max(8, Math.round(pm25 * s.mult + s.offset))
        const sRisk  = stationRisk(sPm25)
        const sColor = RISK_COLOR[sRisk]
        const delta  = sPm25 - mainPm25
        const deltaStr = s.id === 0
          ? 'Trạm tham chiếu chính'
          : delta > 0 ? `+${delta} so với cổng chính` : `${delta} so với cổng chính`

        return (
          <Fragment key={s.id}>
            <Circle
              center={s.pos}
              radius={22}
              pathOptions={{ color: sColor, fillColor: sColor, fillOpacity: 0.09, weight: 0.5, opacity: 0.3 }}
            />
            <Marker position={s.pos} icon={makeIcon(sColor, s.main)}>
              <Popup closeButton={false} minWidth={175}>
                <div style={{ fontFamily: 'DM Sans, sans-serif', padding: '4px 2px' }}>
                  <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 10, marginBottom: 6, lineHeight: 1.4 }}>
                    <span style={{ color: 'rgba(255,255,255,0.78)', fontWeight: 600 }}>{s.label}</span>
                    {' · '}{s.sublabel}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: sColor, display: 'inline-block', flexShrink: 0 }} />
                    <span style={{ color: sColor, fontSize: 10, fontWeight: 700, letterSpacing: '0.07em' }}>
                      {RISK_LABEL[sRisk]}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 5, marginBottom: 8 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 600, color: sColor, lineHeight: 1 }}>
                      {sPm25}
                    </span>
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>µg/m³</span>
                  </div>

                  <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.38)', lineHeight: 1.45, marginBottom: 8 }}>
                    {HEALTH_NOTE[sRisk]}
                  </p>

                  <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.22)', borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 7, margin: 0 }}>
                    {deltaStr}
                  </p>
                </div>
              </Popup>
            </Marker>
          </Fragment>
        )
      })}

      <MapResizer />
    </MapContainer>
  )
}
