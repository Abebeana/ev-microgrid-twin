import { type Alarm } from '@/shared/api/contracts/alarms'
import { type Availability } from '@/shared/api/contracts/capabilities'
import { type Session } from '@/shared/api/contracts/charging'
import { type ScenarioResult } from '@/shared/api/contracts/scenarios'
import { type MicrogridSite } from '@/shared/api/contracts/site'
import {
  type MeasurementQuality,
  type TelemetrySnapshot,
  type TelemetryTrend,
} from '@/shared/api/contracts/telemetry'
import { type AssetGraph } from '@/shared/api/contracts/topology'
import { createContext, useContext } from 'react'

export type ReplayContextValue = {
  site: MicrogridSite
  snapshot: TelemetrySnapshot
  trend: TelemetryTrend
  alarms: Alarm[]
  quality: MeasurementQuality
  graph: AssetGraph
  availability: Availability
  sessions: Session[]
  rawTime: string
  setRawTime: (value: string) => void
  hours: number
  setHours: (value: number) => void
  selectedBox: string | null
  selectBox: (id: string) => void
  navigate: (path: string) => void
  refresh: () => void
  scenarioA: ScenarioResult | null
  setScenarioA: (value: ScenarioResult) => void
  scenarioB: ScenarioResult | null
  setScenarioB: (value: ScenarioResult) => void
}

export const ReplayContext = createContext<ReplayContextValue | null>(null)
export const NavigationContext = createContext<Pick<
  ReplayContextValue,
  'navigate' | 'setRawTime'
> | null>(null)
export function useReplay(): ReplayContextValue {
  const value = useContext(ReplayContext)
  if (!value) throw new Error('Twin context is unavailable')
  return value
}
export function useNavigation() {
  const value = useContext(NavigationContext)
  if (!value) throw new Error('Navigation context is unavailable')
  return value
}
