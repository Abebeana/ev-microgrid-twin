import { type GraphAnalytics, type GraphHistory } from '@/shared/api/contracts/topology'

export type TelemetryStreamStatus = {
  mode: 'simulated_historical_stream'
  topic: string
  broker_connected: boolean
  fresh: boolean
  age_seconds: number | null
  accepted: number
  rejected: number
  last_error: string | null
  storage_error?: string | null
  latest: null | {
    run_id: string
    sequence: number
    recorded_at: string
    emitted_at: string
    received_at: string
    solar_kw: number | null
    observed_ev_kw: number | null
    battery_soc_pct: number | null
    battery_temp_c: number | null
    reporting_wallboxes: number
    pv_minus_observed_ev_kw: number | null
    alerts: string[]
    wallboxes: {
      id: string
      power_kw: number | null
      status: string
      status_stale: boolean
    }[]
  }
  history: {
    recorded_at: string
    solar_kw: number | null
    observed_ev_kw: number | null
    battery_soc_pct: number | null
  }[]
}

export type StreamTopology = {
  mode: string
  store: string
  nodes: {
    id: string
    kind: string
    name?: string
    value?: number | null
    status?: string
    recorded_at?: string
  }[]
  edges: { source: string; target: string; relation: string }[]
  analytics?: GraphAnalytics
  history?: GraphHistory
  error?: string
}
