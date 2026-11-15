import type { Wallbox } from '@/shared/api/contracts/charging'
export type TelemetrySnapshot = {
  mode: string
  raw_time: string
  site_time: string
  source_timezone_interpretation: string
  solar_kw: number | null
  solar_samples: number
  battery_soc_pct: number | null
  battery_temp_c: number | null
  p_sum_kw: number | null
  observed_charging_kw: number | null
  observed_wallboxes: number
  active_sessions: number
  total_wallboxes: number
  wallboxes: Wallbox[]
  unavailable: Record<string, string>
}

export type TrendPoint = {
  raw_time: string
  site_time: string
  solar_kw: number | null
  battery_soc_pct: number | null
  observed_charging_kw: number | null
  observed_wallboxes: number
  solar_minutes: number
  charging_minutes: number
}

export type TelemetryTrend = {
  hours: number
  bin_minutes: number
  points: TrendPoint[]
}

export type MeasurementQuality = {
  checks: { code: string; count: number; detail: string }[]
  metadata: Record<string, string>
  minutes: { minutes: number; solar_minutes: number; bad_soc: number }
}
