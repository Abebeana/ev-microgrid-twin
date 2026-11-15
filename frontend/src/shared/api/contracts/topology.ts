export type GraphNode = {
  id: string
  kind: 'solar' | 'battery' | 'bus' | 'other' | 'charger' | 'site' | 'telemetry_sample' | 'alert'
  name: string
  value: number | null
  wallbox_id: string | null
  status?: string
  recorded_at?: string
  rule?: string
  attribution?: string
}

export type GraphEdge = {
  source: string
  target: string
  relation?: string
}

export type GraphAnalytics = {
  engine: string
  utility_nodes: number
  islanded: boolean
  census: {
    labels: { label: string; count: number }[]
    relations: { relation: string; count: number }[]
  }
  downstream: {
    charger_id: string
    name: string
    power_kw: number | null
    status: string | null
    path: string[]
  }[]
  electrical_paths: { source: string; target: string; hops: string[] }[]
  alerts: {
    id: string
    rule: string
    message: string
    about: string[]
    exposed: string[]
  }[]
  attribution: { id: string; kind: string; attribution: string | null; attributed: boolean }[]
  queries: { name: string; cypher: string }[]
}

export type GraphHistory = {
  samples: number
  alerts: number
  recent: { recorded_at: string; alert_count: number; rules: string[] }[]
  charger_trace: {
    charger_id: string
    name: string
    recorded_at: string
    power_kw: number | null
    status: string | null
  }[]
  repeated_exposure: {
    rule: string
    asset_id: string
    asset_name: string | null
    minutes: number
    exposed: string[]
  }[]
}

export type AssetGraph = {
  nodes: GraphNode[]
  edges: GraphEdge[]
  note: string
  store: string
  analytics: GraphAnalytics
  history: GraphHistory
}
