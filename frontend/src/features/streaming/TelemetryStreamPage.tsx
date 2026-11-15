import { type StreamTopology, type TelemetryStreamStatus } from '@/shared/api/contracts/streaming'
import { getJson } from '@/shared/api/http-client'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'
import { MetricStrip } from '@/shared/components/MetricStrip'
import { UnavailableState } from '@/shared/components/UnavailableState'
import { formatPercent, formatPower } from '@/shared/format/measurements'
import { useNavigation } from '@/shared/state/replay-context'
import { Button } from '@/shared/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ShieldCheck } from 'lucide-react'

export function TelemetryStreamPage() {
  const { navigate, setRawTime } = useNavigation()
  const query = useQuery({
    queryKey: ['demo-stream'],
    queryFn: () => getJson<TelemetryStreamStatus>('/api/demo-stream'),
    refetchInterval: 2000,
  })
  const graphQuery = useQuery({
    queryKey: ['demo-stream-graph'],
    queryFn: () => getJson<StreamTopology>('/api/demo-stream/graph'),
    refetchInterval: 2000,
  })
  if (query.isError)
    return (
      <div className="load-error" role="alert">
        <strong>Stream status is unavailable.</strong>
        <p>{String(query.error)}</p>
        <Button className="action-button" onClick={() => query.refetch()}>
          Retry
        </Button>
      </div>
    )
  if (!query.data) return <div className="loading-state">Checking MQTT replay stream…</div>
  const status = query.data
  const frame = status.latest
  const inspect = () => {
    if (!frame) return
    setRawTime(frame.recorded_at.slice(0, 16))
    navigate('/')
  }
  const scale = Math.max(
    1,
    ...status.history.flatMap((point) => [point.solar_kw ?? 0, point.observed_ev_kw ?? 0]),
  )
  return (
    <>
      <div className="stream-status" role="status">
        <span className={status.fresh ? 'stream-pulse is-fresh' : 'stream-pulse'} />
        {status.fresh ? 'Receiving' : status.broker_connected ? 'Waiting' : 'Broker down'}
        <code>{status.topic}</code>
      </div>
      <MetricStrip
        items={[
          {
            label: 'Solar at recorded minute',
            value: formatPower(frame?.solar_kw),
            caption: '',
          },
          {
            label: 'Observed EV load',
            value: formatPower(frame?.observed_ev_kw),
            caption: `${frame?.reporting_wallboxes ?? 0}/${frame?.wallboxes.length ?? 0} wallboxes reporting`,
          },
          {
            label: 'Battery SoC',
            value: formatPercent(frame?.battery_soc_pct),
            caption: '',
          },
          {
            label: 'Message age',
            value: status.age_seconds == null ? 'No message' : `${status.age_seconds.toFixed(0)} s`,
            caption: status.fresh ? 'Recent broker receipt' : 'Stale or not yet received',
          },
        ]}
      />
      <div className="content-grid">
        <DataPanel title="Streamed measurements" className="wide">
          {status.history.length ? (
            <>
              <div
                className="stream-chart"
                role="img"
                aria-label="Recent solar and observed EV power in the simulated MQTT stream"
              >
                {status.history.map((point, index) => (
                  <div
                    className="stream-chart-column"
                    key={`${point.recorded_at}-${index}`}
                    title={`${point.recorded_at} · solar ${formatPower(point.solar_kw)} · EV ${formatPower(point.observed_ev_kw)}`}
                  >
                    {point.solar_kw != null && (
                      <i
                        className="stream-solar"
                        style={{ height: `${(point.solar_kw / scale) * 100}%` }}
                      />
                    )}
                    {point.observed_ev_kw != null && (
                      <i
                        className="stream-ev"
                        style={{
                          height: `${(point.observed_ev_kw / scale) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                ))}
              </div>
              <div className="stream-legend">
                <span>
                  <i className="stream-solar" /> Solar
                </span>
                <span>
                  <i className="stream-ev" /> Observed EV
                </span>
              </div>
              <details className="chart-data">
                <summary>View streamed chart values</summary>
                <div className="table-scroll">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Recorded source time</TableHead>
                        <TableHead>Solar</TableHead>
                        <TableHead>Observed EV</TableHead>
                        <TableHead>Battery SoC</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {status.history.map((point, index) => (
                        <TableRow key={`${point.recorded_at}-${index}`}>
                          <TableHead scope="row">{point.recorded_at.replace('T', ' ')}</TableHead>
                          <TableCell>{formatPower(point.solar_kw)}</TableCell>
                          <TableCell>{formatPower(point.observed_ev_kw)}</TableCell>
                          <TableCell>{formatPercent(point.battery_soc_pct)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </details>
            </>
          ) : (
            <UnavailableState title="No messages received yet" reason="No frames yet." />
          )}
        </DataPanel>
        <DataPanel title="Ingestion checks">
          <DetailList
            rows={[
              { label: 'Accepted frames', value: status.accepted },
              { label: 'Rejected frames', value: status.rejected },
              {
                label: 'Last validation error',
                value: status.last_error ?? 'None',
              },
              {
                label: 'Graph store',
                value: status.storage_error ? 'Neo4j unavailable' : 'Neo4j',
              },
              {
                label: 'Recorded source time',
                value: frame?.recorded_at.replace('T', ' ') ?? 'Waiting',
              },
              {
                label: 'Received by API',
                value: frame?.received_at
                  ? new Date(frame.received_at).toLocaleString()
                  : 'Waiting',
              },
              {
                label: 'Publisher run',
                value: frame?.run_id ? <code className="hash">{frame.run_id}</code> : 'Waiting',
              },
              { label: 'Sequence', value: frame?.sequence ?? 'Waiting' },
              {
                label: 'Source type',
                value: 'Historical data, simulated transport',
              },
            ]}
          />
          {frame && (
            <Button className="action-button" onClick={inspect}>
              Inspect recorded minute <ArrowRight size={15} />
            </Button>
          )}
        </DataPanel>
        <DataPanel title="Derived state" className="wide">
          {frame ? (
            <>
              <div className="stream-insight">
                <ShieldCheck size={20} />
                <div>
                  <strong>
                    {frame.alerts.length
                      ? `${frame.alerts.length} condition${frame.alerts.length === 1 ? '' : 's'} to review`
                      : 'No configured condition triggered'}
                  </strong>
                </div>
              </div>
              {frame.alerts.length ? (
                <ul className="stream-alerts">
                  {frame.alerts.map((alert) => (
                    <li key={alert}>{alert}</li>
                  ))}
                </ul>
              ) : null}
              <div className="stream-subset">
                PV minus observed EV load{' '}
                <strong>{formatPower(frame.pv_minus_observed_ev_kw)}</strong>
              </div>
            </>
          ) : (
            <p className="quiet">Waiting for a frame.</p>
          )}
        </DataPanel>
        <DataPanel title="Charger entities">
          {frame ? (
            <div className="table-scroll">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Wallbox</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Power</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {frame.wallboxes.map((box) => (
                    <TableRow key={box.id}>
                      <TableHead scope="row">{box.id}</TableHead>
                      <TableCell>
                        {box.status}
                        {box.status_stale ? ' · old event' : ''}
                      </TableCell>
                      <TableCell>{formatPower(box.power_kw)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="quiet">Waiting.</p>
          )}
        </DataPanel>
        <DataPanel title="Current stream graph" className="full">
          {graphQuery.isError ? (
            <p className="error-text">Graph service unavailable: {String(graphQuery.error)}</p>
          ) : graphQuery.data?.nodes.length ? (
            <>
              <div className="graph-summary">
                <div>
                  <strong>{graphQuery.data.nodes.length}</strong>
                  <span>entity nodes</span>
                </div>
                <div>
                  <strong>{graphQuery.data.edges.length}</strong>
                  <span>typed relationships</span>
                </div>
                <div>
                  <strong>{new Set(graphQuery.data.nodes.map((node) => node.kind)).size}</strong>
                  <span>entity types</span>
                </div>
              </div>
              {graphQuery.data.analytics && (
                <p className="graph-note">
                  {graphQuery.data.analytics.downstream.length} chargers traced from the islanded
                  bus.
                  {graphQuery.data.history
                    ? ` ${graphQuery.data.history.samples} minutes retained in Neo4j.`
                    : ''}
                </p>
              )}
              <div className="graph-kind-list">
                {Array.from(new Set(graphQuery.data.nodes.map((node) => node.kind))).map((kind) => (
                  <span key={kind}>
                    {kind.replaceAll('_', ' ')}{' '}
                    <b>{graphQuery.data!.nodes.filter((node) => node.kind === kind).length}</b>
                  </span>
                ))}
              </div>
              <details className="chart-data">
                <summary>Inspect graph relationships</summary>
                <div className="table-scroll">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>From</TableHead>
                        <TableHead>Relation</TableHead>
                        <TableHead>To</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {graphQuery.data.edges.map((edge) => (
                        <TableRow key={`${edge.source}-${edge.target}`}>
                          <TableCell>{edge.source}</TableCell>
                          <TableCell>{edge.relation.replaceAll('_', ' ')}</TableCell>
                          <TableCell>{edge.target}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </details>
              <Button className="text-link" onClick={() => navigate('/graph')}>
                Topology <ArrowRight size={13} />
              </Button>
            </>
          ) : (
            <p className="quiet">Waiting for a frame.</p>
          )}
        </DataPanel>
      </div>
    </>
  )
}
