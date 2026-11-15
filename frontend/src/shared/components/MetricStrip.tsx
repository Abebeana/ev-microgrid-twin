export function MetricStrip({
  items,
}: {
  items: { label: string; value: string; caption?: string }[]
}) {
  return (
    <div className="metrics-strip">
      {items.map((item) => (
        <div className="metric" key={item.label}>
          <div className="metric-label">{item.label}</div>
          <div className="metric-value">{item.value}</div>
          {item.caption && <div className="metric-caption">{item.caption}</div>}
        </div>
      ))}
    </div>
  )
}
