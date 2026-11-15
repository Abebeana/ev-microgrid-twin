import { Button } from '@/shared/ui/button'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

import { useQuery } from '@tanstack/react-query'

import { ArrowRight, CircleCheck, Database, HardDrive, Network } from 'lucide-react'

import { getJson } from '@/shared/api/http-client'

import { type TelemetryStreamStatus } from '@/shared/api/contracts/streaming'
import { formatSiteTime } from '@/shared/format/time'

import { useReplay } from '@/shared/state/replay-context'

import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'

export function SystemHealthPage() {
  const { availability, quality, site, navigate } = useReplay()
  const stream = useQuery({
    queryKey: ['demo-stream-health'],
    queryFn: () => getJson<TelemetryStreamStatus>('/api/demo-stream'),
    refetchInterval: 5000,
  })
  const service = useQuery({
    queryKey: ['service-health'],
    queryFn: () =>
      getJson<{ graph: { store: string; connected: boolean; detail?: string } }>('/api/health'),
    refetchInterval: 10000,
  })
  const audit = useQuery({
    queryKey: ['audit'],
    queryFn: () =>
      getJson<
        {
          id: number
          occurred_at: string
          actor: string
          action: string
          target: string
        }[]
      >('/api/audit'),
  })
  return (
    <>
      <MetricStrip
        items={[
          {
            label: 'Replay store',
            value: 'Ready',
            caption: `${Number(quality.metadata.microgrid_minutes).toLocaleString()} microgrid minutes`,
          },
          {
            label: 'Live source',
            value: availability.live.available ? 'Connected' : 'Not connected',
            caption: availability.live.reason,
          },
          {
            label: 'Control',
            value: availability.control.available ? 'Configured' : 'Advisory only',
            caption: availability.control.reason,
          },
          {
            label: 'MQTT demo',
            value: stream.isError ? 'Unavailable' : stream.data?.fresh ? 'Receiving' : 'Waiting',
            caption: stream.isError
              ? 'Stream status could not be loaded'
              : stream.data?.fresh
                ? `${stream.data.accepted} accepted frames`
                : 'Historical replay transport',
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Architecture & health" className="wide">
          <div className="pipeline">
            <div>
              <Database size={22} />
              <strong>Raw JSON</strong>
              <small>Read-only · source hash recorded</small>
            </div>
            <ArrowRight size={18} />
            <div>
              <HardDrive size={22} />
              <strong>Replay files</strong>
              <small>Indexed historical queries</small>
            </div>
            <ArrowRight size={18} />
            <div>
              <CircleCheck size={22} />
              <strong>Operations API</strong>
              <small>Typed contracts and audit</small>
            </div>
            <ArrowRight size={18} />
            <div>
              <Network size={22} />
              <strong>Neo4j</strong>
              <small>
                {service.data?.graph.connected
                  ? 'Property graph connected'
                  : service.isError
                    ? 'Health check failed'
                    : service.data
                      ? 'Graph store unavailable'
                      : 'Checking the graph store'}
              </small>
            </div>
          </div>
          <DetailList
            rows={[
              {
                label: 'Source SHA-256',
                value: <code className="hash">{quality.metadata.source_sha256}</code>,
              },
              {
                label: 'Source time',
                value: site.config.source_timestamp_timezone,
              },
              { label: 'Site time', value: site.config.site_timezone },
              { label: 'Review mode', value: 'Local prototype' },
              {
                label: 'Graph store',
                value: service.isLoading
                  ? 'Checking'
                  : service.data?.graph.connected
                    ? 'Neo4j'
                    : 'Unavailable',
              },
            ]}
          />
        </DataPanel>
        <DataPanel title="Capability readiness">
          <Button className="text-link" onClick={() => navigate('/stream')}>
            Inspect simulated MQTT stream <ArrowRight size={13} />
          </Button>
          <div className="readiness-list">
            {Object.entries(availability).map(([name, state]) => (
              <div key={name}>
                <span className={state.available ? 'good' : 'muted-dot'} />
                <strong>{name}</strong>
                <small>{state.reason}</small>
              </div>
            ))}
          </div>
        </DataPanel>
        <DataPanel title="Local audit trail" className="full">
          {audit.isError ? (
            <p className="error-text">{String(audit.error)}</p>
          ) : audit.data?.length ? (
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Actor</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Target</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {audit.data.map((event) => (
                    <TableRow key={event.id}>
                      <TableCell>{formatSiteTime(event.occurred_at)}</TableCell>
                      <TableCell>{event.actor}</TableCell>
                      <TableCell>{event.action}</TableCell>
                      <TableCell>
                        <code>{event.target}</code>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="quiet">No review actions recorded yet.</p>
          )}
        </DataPanel>
      </div>
    </>
  )
}
