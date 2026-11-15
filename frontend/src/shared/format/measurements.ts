export const formatPower = (value: number | null | undefined) =>
  value == null ? 'Unavailable' : `${value.toFixed(2)} kW`
export const formatPercent = (value: number | null | undefined) =>
  value == null ? 'Unavailable' : `${value.toFixed(1)}%`
