import { useReplay } from '@/shared/state/replay-context'

export function SiteTelemetryTrend() {
  const { trend } = useReplay()
  const values = [
    trend.points.map((p) => p.solar_kw),
    trend.points.map((p) => p.observed_charging_kw),
  ]
  const max = Math.max(1, ...values.flat().filter((v): v is number => v != null))
  const lines = (arr: (number | null)[]) => {
    const result: string[] = []
    let path = ''
    arr.forEach((v, i) => {
      if (v == null) {
        if (path) result.push(path)
        path = ''
        return
      }
      const x = 40 + (i / Math.max(1, arr.length - 1)) * 920
      const y = 180 - (v / max) * 142
      path += (path ? ' L' : 'M') + x.toFixed(1) + ',' + y.toFixed(1)
    })
    if (path) result.push(path)
    return result
  }
  return (
    <div className="site-trend">
      <svg
        viewBox="0 0 1000 210"
        preserveAspectRatio="none"
        role="img"
        aria-label="Measured solar and observed charging power trend"
      >
        {[38, 85, 132, 180].map((y) => (
          <line key={y} x1="40" x2="960" y1={y} y2={y} stroke="#35505b" strokeDasharray="3 6" />
        ))}
        {lines(values[0]).map((d, i) => (
          <path
            key={'pv' + i}
            d={d}
            fill="none"
            stroke="#8faf86"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {lines(values[1]).map((d, i) => (
          <path
            key={'ev' + i}
            d={d}
            fill="none"
            stroke="#e9bf7d"
            strokeWidth="3"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      <div className="site-trend-legend">
        <span>
          <i className="pv" /> PV
        </span>
        <span>
          <i className="ev" /> EV
        </span>
        <span>0–{max.toFixed(1)} kW</span>
      </div>
    </div>
  )
}
