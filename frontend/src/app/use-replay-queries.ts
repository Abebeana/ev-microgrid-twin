import { type Alarm } from '@/shared/api/contracts/alarms'
import { type Availability } from '@/shared/api/contracts/capabilities'
import { type Session } from '@/shared/api/contracts/charging'
import { type MicrogridSite } from '@/shared/api/contracts/site'
import {
  type MeasurementQuality,
  type TelemetrySnapshot,
  type TelemetryTrend,
} from '@/shared/api/contracts/telemetry'
import { type AssetGraph } from '@/shared/api/contracts/topology'
import { rawAt } from '@/shared/format/time'
import { getJson } from '@/shared/api/http-client'
import { useQuery } from '@tanstack/react-query'

export function useReplayQueries(path: string, rawTimeOverride: string | null, hours: number) {
  const streamPath = path === '/stream'
  const site = useQuery({
    queryKey: ['site'],
    queryFn: () => getJson<MicrogridSite>('/api/site'),
    enabled: !streamPath,
  })
  const rawTime = rawTimeOverride ?? site.data?.default_raw.replace(' ', 'T') ?? ''
  const at = rawTime ? encodeURIComponent(rawAt(rawTime)) : ''
  const replay = useQuery({
    queryKey: ['replay', rawTime],
    queryFn: () => getJson<TelemetrySnapshot>(`/api/replay?at=${at}`),
    enabled: Boolean(rawTime) && !streamPath,
    placeholderData: path === '/site' ? (previous) => previous : undefined,
  })
  const trend = useQuery({
    queryKey: ['trend', rawTime, hours],
    queryFn: () => getJson<TelemetryTrend>(`/api/trend?at=${at}&hours=${hours}`),
    enabled: Boolean(rawTime) && !streamPath,
    placeholderData: path === '/site' ? (previous) => previous : undefined,
  })
  const alarms = useQuery({
    queryKey: ['alarms', rawTime],
    queryFn: () => getJson<Alarm[]>(`/api/alarms?at=${at}`),
    enabled: Boolean(rawTime) && !streamPath,
    placeholderData: path === '/site' ? (previous) => previous : undefined,
  })
  const sessions = useQuery({
    queryKey: ['sessions', rawTime],
    queryFn: () => getJson<Session[]>(`/api/sessions?at=${at}`),
    enabled: Boolean(rawTime) && !streamPath,
    placeholderData: path === '/site' ? (previous) => previous : undefined,
  })
  const graph = useQuery({
    queryKey: ['graph', rawTime],
    queryFn: () => getJson<AssetGraph>(`/api/graph?at=${at}`),
    enabled: Boolean(rawTime) && !streamPath,
    placeholderData: path === '/site' ? (previous) => previous : undefined,
  })
  const quality = useQuery({
    queryKey: ['quality'],
    queryFn: () => getJson<MeasurementQuality>('/api/quality'),
    enabled: !streamPath,
  })
  const availability = useQuery({
    queryKey: ['availability'],
    queryFn: () => getJson<Availability>('/api/availability'),
    enabled: !streamPath,
  })
  return { site, replay, trend, alarms, sessions, graph, quality, availability, rawTime }
}
