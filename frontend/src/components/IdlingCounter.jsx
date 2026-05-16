import { useEffect, useRef, useState } from 'react'

export default function IdlingCounter({ count = 0 }) {
  const prev = useRef(count)
  const [key, setKey] = useState(0)

  useEffect(() => {
    if (prev.current !== count) {
      setKey(k => k + 1)
      prev.current = count
    }
  }, [count])

  const trend = count > prev.current ? 'up' : count < prev.current ? 'down' : 'same'

  return (
    <div className="card p-5 flex flex-col gap-3">
      <p className="stat-label">Phương tiện đang nổ máy</p>
      <div className="flex items-end gap-3">
        <span key={key} className="stat-value text-amber-300 animate-count_up">{count}</span>
        {trend === 'up' && (
          <span className="mb-1 text-red-400 text-sm font-medium flex items-center gap-0.5">
            ▲ tăng
          </span>
        )}
        {trend === 'down' && (
          <span className="mb-1 text-lime-400 text-sm font-medium flex items-center gap-0.5">
            ▼ giảm
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {Array.from({ length: Math.min(count, 12) }).map((_, i) => (
            <div key={i} className="w-2 h-4 rounded-sm bg-amber-400/70" />
          ))}
          {count > 12 && <span className="text-amber-400/60 text-xs self-end">+{count - 12}</span>}
        </div>
      </div>
      <p className="text-xs text-white/30">Ước tính từ phân tích camera</p>
    </div>
  )
}
